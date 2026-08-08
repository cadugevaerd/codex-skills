#!/usr/bin/env python3
"""Safe workflow bootstrap plus a read-only lifecycle hook (stdlib only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = "v2"
MARKER = "grill-with-docs-workflow:v2"
HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[1] / "assets/WORKFLOW.template.md"
ESSENTIAL = (
    "## Loop externo",
    "## Ciclo externo de execução",
    "specify",
    "plan",
    "checklist",
    "tasks",
    "analyze",
    "agent-assign",
    "agent-execute",
    "converge",
    "verify",
    "review",
    "ship",
    "PLAN_ONLY_STOP",
    "Spec Kit >=0.11.2",
    "A–E",
    "no PR",
    "hotfix-fast",
    "HOTFIX-GO",
)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def git_root(path: Path) -> Path | None:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return Path(output.strip()).resolve()


def compatible(text: str) -> bool:
    return bool(text.strip()) and all(item in text for item in ESSENTIAL)


def managed_version(text: str) -> str | None:
    match = re.search(r"grill-with-docs-workflow:(v\d+)", text)
    return match.group(1) if match else None


def read_regular(path: Path) -> tuple[bytes, str]:
    """Open one regular file without following a final-component symlink."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    content = b"".join(chunks)
    return content, content.decode("utf-8")


def emit(status: str, path: Path | None = None, content: bytes | None = None, **extra: str) -> None:
    payload: dict[str, str] = {"status": status, **extra}
    if path is not None and content is not None:
        payload.update(path=str(path), sha256=digest(content), version=VERSION)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def atomic_create(target: Path, content: bytes) -> bool:
    """Create target exactly once; never replace an existing directory entry."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
            created = True
        except FileExistsError:
            created = False
        try:
            directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            directory_descriptor = os.open(target.parent, directory_flags)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError:
            # Directory fsync is unavailable on some supported filesystems.
            pass
        return created
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def ensure(root_argument: str) -> int:
    candidate = Path(root_argument).expanduser()
    if not candidate.is_dir():
        emit("BLOCKED", reason="ROOT must be existing Git top-level")
        return 2
    root = candidate.resolve()
    if git_root(root) != root:
        emit("BLOCKED", reason="ROOT must be existing Git top-level")
        return 2

    target = root / "WORKFLOW.md"
    try:
        if target.is_symlink() or target.resolve(strict=False).parent != root:
            emit("BLOCKED", reason="unsafe target")
            return 2

        if target.exists():
            content, text = read_regular(target)
            version = managed_version(text)
            if version and version != VERSION:
                emit("BLOCKED", reason="managed version mismatch")
                return 2
            if compatible(text):
                emit("REUSED", target, content)
                return 0
            emit("BLOCKED", reason="incompatible workflow")
            return 2

        template_content, template_text = read_regular(TEMPLATE)
        if managed_version(template_text) != VERSION or not compatible(template_text):
            emit("BLOCKED", reason="invalid bundled template")
            return 2
        created = atomic_create(target, template_content)

        if target.is_symlink() or target.resolve(strict=False).parent != root:
            emit("BLOCKED", reason="unsafe target after create")
            return 2
        content, text = read_regular(target)
        version = managed_version(text)
        if (version and version != VERSION) or not compatible(text):
            emit("BLOCKED", reason="read-back validation failed")
            return 2
        emit("CREATED" if created else "REUSED", target, content)
        return 0
    except UnicodeError:
        emit("BLOCKED", reason="invalid UTF-8 workflow")
        return 2
    except OSError as error:
        emit("BLOCKED", reason=f"filesystem-error:{type(error).__name__}")
        return 2


def human_status(payload: dict, root: Path) -> str:
    items = payload.get("items") or payload.get("work_items") or []
    count = len(items) if isinstance(items, list) else 0
    branch = payload.get("branch", "?"); head = str(payload.get("head", "?"))[:12]
    phase = payload.get("phase") or payload.get("active_phase") or "?"
    du = payload.get("development_type") or payload.get("type") or "?"
    step = payload.get("current_step") or "?"
    blockers = payload.get("blockers") or payload.get("findings") or []
    if isinstance(blockers, list): blockers = ", ".join(map(str, blockers[:3])) or "nenhum"
    next_gate = payload.get("next_gate") or "checkpoint"
    return f"Itens: {count}; branch={branch}; head={head}; fase={phase}; DU/type={du}; etapa={step}/11; próximo gate={next_gate}; blockers={blockers}. Comando: grill_workspace.py status {root}"


def hook() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError, UnicodeError):
        emit("BLOCKED", reason="invalid-json")
        return 0
    if not isinstance(payload, dict):
        emit("BLOCKED", reason="invalid-payload")
        return 0

    event = payload.get("hook_event_name")
    if event not in ("SessionStart", "SubagentStart"):
        emit("IGNORED")
        return 0
    root = git_root(Path(payload.get("cwd") or os.getcwd()))
    if root is None:
        emit("BLOCKED", reason="invalid-root")
        return 0

    path = root / "WORKFLOW.md"
    if path.is_symlink() or (path.exists() and path.resolve(strict=False).parent != root):
        message = f"WORKFLOW.md inseguro em {path}; invoque grill-with-docs para auditar."
    elif not path.is_file():
        message = f"WORKFLOW.md ausente em {root}; invoque grill-with-docs para preparar o workflow."
    else:
        try:
            content, text = read_regular(path)
        except (OSError, UnicodeError):
            content, text = b"", ""
        if managed_version(text) == VERSION and compatible(text):
            try:
                status_script = HERE.with_name("grill_workspace.py")
                result = subprocess.run([sys.executable, str(status_script), "status", str(root), "--current-worktree"], capture_output=True, text=True, check=False, timeout=3)
                status_payload = json.loads(result.stdout.strip()) if result.stdout.strip() else {"verdict":"BLOCKED"}
                status_line = human_status(status_payload, root) if isinstance(status_payload, dict) else "BLOCKED status"
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
                status_line = "BLOCKED status"
            message = (f"Leia {path}; sha256={digest(content)}. {status_line} "
                       "Fluxo: specify → plan → checklist → tasks → analyze → agent-assign → agent-execute → converge → verify → review → ship.")
        else:
            message = f"WORKFLOW.md incompatível em {path}; invoque grill-with-docs para auditar."

    output = {
        "status": "OK",
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": message,
        },
    }
    rendered = json.dumps(output, ensure_ascii=False, sort_keys=True)
    if len(rendered) > 2048:
        marker = "[TRUNCATED]"
        context = message
        while len(rendered) > 2048 and context:
            context = context[: max(0, len(context) - 128)]
            output["hookSpecificOutput"]["additionalContext"] = context.rstrip() + marker
            rendered = json.dumps(output, ensure_ascii=False, sort_keys=True)
        if len(rendered) > 2048:
            output["hookSpecificOutput"]["additionalContext"] = marker
            rendered = json.dumps(output, ensure_ascii=False, sort_keys=True)
    print(rendered)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ensure")
    group.add_argument("--hook", action="store_true")
    arguments = parser.parse_args(argv)
    return hook() if arguments.hook else ensure(arguments.ensure)


if __name__ == "__main__":
    raise SystemExit(main())
