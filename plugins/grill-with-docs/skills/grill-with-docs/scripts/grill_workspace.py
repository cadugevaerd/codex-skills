#!/usr/bin/env python3
"""Deterministic isolated work-item lifecycle for grill-with-docs v2 (stdlib only)."""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

EXIT_OK = 0
EXIT_NO_GO = 1
EXIT_BLOCKED = 2
EXIT_CONSTITUTION = 3
KINDS = {"feature", "fix", "hotfix"}
WORK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,100}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
ADR_RE = re.compile(r"\bADR-\d{4}\b")
DQ_RE = re.compile(r"\bDQ-\d{4}\b")
BL_RE = re.compile(r"\bBL-\d{4}\b")
PHASE_RE = re.compile(r"\bFASE-\d{3}\b")
ROUND_RE = re.compile(r"\bR-\d{4}\b")
ASSETS = Path(__file__).resolve().parents[1] / "assets"
ROOT_FILES = (
    "CONTEXT.md",
    "DECISION-BACKLOG.md",
    "DECISION-FRONTIER.md",
    "ROADMAP.md",
    "ROUND-LOG.jsonl",
    "state.json",
    "PLAN-CONTEXT.md",
    "CONSTITUTION-CHECK.md",
    "AUDIT.md",
)
LEGACY_FILES = tuple(name for name in ROOT_FILES if name != "CONSTITUTION-CHECK.md")
MANAGED_GLOBAL = {".grill/global/ROADMAP.md", ".grill/global/AUDIT.md"}
CHECK_START = "<!-- grill-constitution-check:start -->"
CHECK_END = "<!-- grill-constitution-check:end -->"


class JsonParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", message)


@dataclass
class CliFailure(Exception):
    exit_code: int
    verdict: str
    code: str
    message: str
    findings: list[str] | None = None

    def payload(self) -> dict[str, Any]:
        result: dict[str, Any] = {"verdict": self.verdict, "code": self.code, "error": self.message}
        if self.findings:
            result["findings"] = sorted(set(self.findings))
        return result


@dataclass
class ItemBundle:
    work_id: str
    files: dict[str, bytes]
    origin: str
    fingerprint: str
    metadata: dict[str, Any]


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(root: Path, *args: str, text: bool = True, check: bool = True) -> str | bytes:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=text,
        check=False,
    )
    if check and process.returncode != 0:
        stderr = process.stderr.strip() if text else process.stderr.decode("utf-8", "replace").strip()
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "GIT-ERROR", stderr or "git command failed")
    return process.stdout


def git_optional(root: Path, *args: str) -> str:
    process = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    return process.stdout.strip() if process.returncode == 0 else ""


def project_root(raw: str | Path) -> Path:
    path = Path(raw)
    if not path.is_dir() or path.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ROOT", "root must be a real directory")
    top = git_optional(path, "rev-parse", "--show-toplevel")
    if not top or Path(top).resolve() != path.resolve():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ROOT", "root must be the Git top-level")
    return path.resolve()


def reject_symlink_chain(root: Path, path: Path, *, allow_missing: bool = True) -> None:
    root = root.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PATH-ESCAPE", str(path)) from exc
    cursor = root
    for part in relative.parts:
        if part in {"", ".", ".."}:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PATH-ESCAPE", str(path))
        cursor = cursor / part
        if cursor.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(cursor))
        if not cursor.exists() and allow_missing:
            continue


def ensure_directory(root: Path, relative: str) -> Path:
    target = root / relative
    reject_symlink_chain(root, target)
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.exists():
            if cursor.is_symlink() or not cursor.is_dir():
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-DIRECTORY", str(cursor))
        else:
            cursor.mkdir()
    return target


def safe_read(path: Path, *, root: Path | None = None, utf8: bool = False) -> bytes | str:
    if root is not None:
        reject_symlink_chain(root, path, allow_missing=False)
    if path.is_symlink() or not path.is_file():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-FILE", str(path))
    try:
        data = path.read_bytes()
        return data.decode("utf-8") if utf8 else data
    except UnicodeError as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-UTF8", str(path)) from exc
    except OSError as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "FILESYSTEM", type(exc).__name__) from exc


def atomic_write(root: Path, path: Path, data: bytes) -> bool:
    reject_symlink_chain(root, path)
    if path.exists() and path.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return False
    fd, temporary = tempfile.mkstemp(prefix=".grill-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        return True
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def read_asset(name: str) -> bytes:
    mapping = {
        "CONTEXT.md": "CONTEXT.template.md",
        "DECISION-BACKLOG.md": "DECISION-BACKLOG.template.md",
        "DECISION-FRONTIER.md": "DECISION-FRONTIER.template.md",
        "ROADMAP.md": "ROADMAP.template.md",
        "ROUND-LOG.jsonl": "ROUND-LOG.template.jsonl",
        "PLAN-CONTEXT.md": "PLAN-CONTEXT.template.md",
        "AUDIT.md": "AUDIT.template.md",
    }
    asset = ASSETS / mapping[name]
    return asset.read_bytes()


def validate_constitution_text(text: str) -> None:
    placeholder_patterns = (
        r"\{\{[^}]+\}\}",
        r"\[(?:PROJECT|PRINCIPLE|CONSTITUTION|RATIFICATION|LAST_AMENDED)[A-Z0-9_]*\]",
        r"\bYYYY-MM-DD\b",
    )
    if not text.strip() or any(re.search(pattern, text) for pattern in placeholder_patterns):
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CONSTITUTION-INVALID", "placeholders or empty content")


def constitution_clauses(text: str) -> list[dict[str, str]]:
    clauses: list[dict[str, str]] = []
    seen: set[str] = set()
    containers = {"core principles", "princípios fundamentais", "principios fundamentais"}
    for match in re.finditer(r"(?m)^(#{2,3})\s+(.+?)\s*$", text):
        heading = match.group(2).strip().strip("#").strip()
        normalized = re.sub(r"\s+", " ", heading).strip()
        if normalized.casefold() in containers:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-") or "clause"
        clause_id = slug
        suffix = 2
        while clause_id in seen:
            clause_id = f"{slug}-{suffix}"
            suffix += 1
        seen.add(clause_id)
        clauses.append({"id": clause_id, "heading": normalized})
    if not clauses:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CONSTITUTION-AMBIGUOUS", "no normative H2/H3 headings")
    return clauses


def constitution_info(root: Path) -> tuple[dict[str, Any], str | None, list[dict[str, str]]]:
    path = root / ".specify" / "memory" / "constitution.md"
    if not path.exists():
        return {"state": "not-present", "path": None, "sha256": None}, None, []
    try:
        text = safe_read(path, root=root, utf8=True)
    except CliFailure as failure:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", failure.code, failure.message) from failure
    assert isinstance(text, str)
    validate_constitution_text(text)
    digest = hash_bytes(text.encode("utf-8"))
    return {"state": "present", "path": ".specify/memory/constitution.md", "sha256": digest}, text, constitution_clauses(text)


def check_document(info: dict[str, Any], clauses: list[dict[str, str]], *, pending: bool) -> bytes:
    if info["state"] == "not-present":
        payload = {"constitution_state": "not-present", "constitution_sha256": None, "clauses": []}
    else:
        payload = {
            "constitution_state": "present",
            "constitution_sha256": info["sha256"],
            "clauses": [
                {
                    "id": clause["id"],
                    "heading": clause["heading"],
                    "status": "PENDING" if pending else "PASS",
                    "evidence": [] if pending else ["verified evidence"],
                    "justification": "" if pending else "verified against the work-item artifacts",
                }
                for clause in clauses
            ],
        }
    return (
        "# Constitution Check\n\n"
        + CHECK_START
        + "\n```json\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n"
        + CHECK_END
        + "\n"
    ).encode("utf-8")


def parse_check(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-INVALID-UTF8", "CONSTITUTION-CHECK.md") from exc
    if text.count(CHECK_START) != 1 or text.count(CHECK_END) != 1:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-MARKERS", "managed block missing or duplicated")
    block = text.split(CHECK_START, 1)[1].split(CHECK_END, 1)[0]
    match = re.search(r"```json\s*(\{.*\})\s*```", block, re.DOTALL)
    if not match:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", "JSON block missing")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", exc.msg) from exc
    if not isinstance(value, dict):
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", "root must be object")
    return value


def validate_constitution_check(root: Path, files: dict[str, bytes], recorded: dict[str, Any]) -> dict[str, Any] | None:
    current, text, clauses = constitution_info(root)
    if current["state"] == "not-present":
        if recorded.get("state") != "not-present":
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CONSTITUTION-STALE", "constitution disappeared")
        return None
    if recorded.get("state") != "present" or recorded.get("sha256") != current["sha256"]:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CONSTITUTION-STALE", "constitution hash changed")
    raw = files.get("CONSTITUTION-CHECK.md")
    if raw is None:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-MISSING", "CONSTITUTION-CHECK.md")
    check = parse_check(raw)
    if check.get("constitution_state") != "present" or check.get("constitution_sha256") != current["sha256"]:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-STALE", "constitution hash mismatch")
    entries = check.get("clauses")
    if not isinstance(entries, list):
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", "clauses must be an array")
    expected = {clause["id"]: clause["heading"] for clause in clauses}
    actual: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", "invalid clause entry")
        clause_id = entry["id"]
        if clause_id in actual:
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-DUPLICATE", clause_id)
        actual[clause_id] = entry
    if set(actual) != set(expected):
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-COVERAGE", "missing or unknown clauses")
    for clause_id, heading in expected.items():
        entry = actual[clause_id]
        status = str(entry.get("status", "")).upper()
        evidence = entry.get("evidence")
        justification = entry.get("justification")
        evidence_ok = (isinstance(evidence, str) and bool(evidence.strip())) or (
            isinstance(evidence, list) and bool(evidence) and all(isinstance(value, str) and value.strip() for value in evidence)
        )
        if entry.get("heading") != heading or status not in {"PASS", "NOT-APPLICABLE"} or not evidence_ok or not isinstance(justification, str) or not justification.strip():
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-NOT-APPROVED", clause_id)
    return {"state": "present", "sha256": current["sha256"], "clauses": len(expected)}


def workflow_info(root: Path) -> dict[str, Any]:
    path = root / "WORKFLOW.md"
    if not path.exists():
        return {"path": "WORKFLOW.md", "sha256": None}
    data = safe_read(path, root=root)
    assert isinstance(data, bytes)
    return {"path": "WORKFLOW.md", "sha256": hash_bytes(data)}


def base_information(root: Path, requested: str | None) -> tuple[str, str]:
    head = git_optional(root, "rev-parse", "HEAD")
    if requested:
        target = git_optional(root, "rev-parse", "--verify", requested)
        if not target:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-BASE-REF", requested)
        merge_base = git_optional(root, "merge-base", "HEAD", requested) if head else ""
        return requested, merge_base or target
    upstream = git_optional(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if upstream:
        merge_base = git_optional(root, "merge-base", "HEAD", upstream)
        if merge_base:
            return upstream, merge_base
    return ("HEAD", head) if head else ("UNBORN", "UNBORN")


def immutable_metadata(root: Path, args: argparse.Namespace, work_id: str) -> dict[str, Any]:
    constitution, _, _ = constitution_info(root)
    base_ref, base_commit = base_information(root, getattr(args, "base_ref", None))
    return {
        "schema": "grill-work-item/v2",
        "work_id": work_id,
        "type": args.type,
        "slug": args.slug,
        "branch": git_optional(root, "branch", "--show-current") or "DETACHED",
        "head": git_optional(root, "rev-parse", "HEAD") or "UNBORN",
        "base_ref": base_ref,
        "base_commit": base_commit,
        "constitution": constitution,
        "workflow": workflow_info(root),
    }


def state_template(root: Path, work_id: str, constitution: dict[str, Any], workflow: dict[str, Any]) -> bytes:
    value = json.loads((ASSETS / "state.template.json").read_text(encoding="utf-8"))
    value["work_id"] = work_id
    value["constitution"] = constitution
    value["workflow"] = {**workflow, "version": "v2"}
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def initial_files(root: Path, work_id: str, immutable: dict[str, Any]) -> dict[str, bytes]:
    _, _, clauses = constitution_info(root)
    files = {name: read_asset(name) for name in ROOT_FILES if name not in {"state.json", "CONSTITUTION-CHECK.md"}}
    files["state.json"] = state_template(root, work_id, immutable["constitution"], immutable["workflow"])
    files["CONSTITUTION-CHECK.md"] = check_document(immutable["constitution"], clauses, pending=immutable["constitution"]["state"] == "present")
    files["handoffs/FASE-001-SPECIFY-HANDOFF.md"] = (ASSETS / "PHASE-SPECIFY-HANDOFF.template.md").read_bytes()
    return files


def hotfix_files(root: Path, work_id: str, immutable: dict[str, Any], details: dict[str, str]) -> dict[str, bytes]:
    """Build a prepared, self-contained incident record with no roadmap dependencies."""
    files = {"HOTFIX.md": ("# HOTFIX-PREPARED\n\n" + "\n".join(f"- {key}: {value}" for key, value in details.items()) + "\n\n## Delivery boundary\n\nHOTFIX-GO requires the separate hotfix-go revalidation step. Reconciliation and full documentary audit are post-ship.\n").encode("utf-8")}
    files["state.json"] = (json.dumps({"version": "2.1.1", "status": "prepared", "audit_verdict": "PREPARED", "mode": "hotfix", "work_id": work_id, "post_ship": ["reconcile", "full-document-audit"]}, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    files["CONSTITUTION-CHECK.md"] = check_document(immutable["constitution"], constitution_info(root)[2], pending=True)
    return files


def hotfix_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if not SLUG_RE.fullmatch(args.slug):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-IDENTITY", "slug invalid")
    values = {"scope": args.scope, "reproduction": args.reproduction, "evidence": args.evidence, "correction-test": args.correction_test, "rollback": args.rollback, "constitution-evidence": args.constitution_evidence, "test-command": args.test_command}
    if any(not value.strip() for value in values.values()):
        raise CliFailure(EXIT_NO_GO, "NO-GO", "HOTFIX-INCOMPLETE", "all hotfix evidence fields are required")
    scope_paths = validate_scope(args.scope)
    if args.test_timeout < 1 or args.test_timeout > 300:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-TEST-TIMEOUT", str(args.test_timeout))
        raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-NOT-CLOSED", "scope contains traversal or line break")
    work_id = args.work_id or f"hotfix-{args.slug}-{uuid.uuid4().hex}"
    if not WORK_ID_RE.fullmatch(work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-WORK-ID", work_id)
    target = root / ".grill" / "work-items" / work_id
    lock = acquire_lock(root, work_id, target, reuse_if_target_exists=True)
    try:
        if target.exists():
            bundle = read_local_bundle(root, target)
            validate_bundle_integrity(bundle)
            if bundle.metadata.get("hotfix", {}).get("scope") != args.scope or bundle.metadata.get("scope", {}).get("paths") != scope_paths:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "HOTFIX-IDENTITY-DIVERGENCE", work_id)
            return {"verdict": "HOTFIX-PREPARED", "status": "REUSED", "work_id": work_id, "path": str(target)}, EXIT_OK
        immutable = immutable_metadata(root, argparse.Namespace(type="hotfix", slug=args.slug, base_ref=args.base_ref), work_id)
        constitution = immutable["constitution"]
        if constitution.get("state") == "present":
            evidence = Path(args.constitution_evidence)
            if evidence.is_absolute() or any(part in {"", ".", ".."} for part in evidence.parts):
                raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-CONSTITUTION-EVIDENCE", args.constitution_evidence)
            evidence_path = root / evidence
            text = safe_read(evidence_path, root=root, utf8=True)
            if not isinstance(text, str) or not text.strip():
                raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-CONSTITUTION-EVIDENCE", args.constitution_evidence)
            values["constitution-evidence"] = json.dumps({"path": evidence.as_posix(), "sha256": hash_bytes(text.encode("utf-8"))}, sort_keys=True)
        else:
            values["constitution-evidence"] = "not-present"
        files = hotfix_files(root, work_id, immutable, values)
        if immutable["constitution"].get("state") == "present":
            evidence = json.loads(values["constitution-evidence"])
            payload = {"constitution_state": "present", "constitution_sha256": immutable["constitution"]["sha256"], "clauses": [{"id": clause["id"], "heading": clause["heading"], "status": "PASS", "evidence": [evidence["path"] + "#" + evidence["sha256"]], "justification": "constitution evidence recorded reproducibly"} for clause in constitution_info(root)[2]]}
            files["CONSTITUTION-CHECK.md"] = ("# Constitution Check\n\n" + CHECK_START + "\n```json\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n```\n" + CHECK_END + "\n").encode("utf-8")
        metadata = metadata_document(immutable, files)
        metadata["scope"] = {"paths": scope_paths}
        metadata["hotfix"] = {**values, "closed": True, "test-timeout": args.test_timeout, "post_ship": ["reconcile", "full-document-audit"]}
        metadata["hotfix_sha256"] = hash_bytes(canonical(metadata["hotfix"]))
        staging = write_bundle_staging(root, work_id, metadata, files)
        try:
            rename_child(target.parent, staging, target)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return {"verdict": "HOTFIX-PREPARED", "status": "CREATED", "work_id": work_id, "path": str(target), "mode": "hotfix-fast", "post_ship": metadata["hotfix"]["post_ship"]}, EXIT_OK
    finally:
        if lock is not None:
            shutil.rmtree(lock, ignore_errors=True)


def metadata_document(immutable: dict[str, Any], files: dict[str, bytes], *, migration: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "grill-work-item/v2",
        "immutable": immutable,
        "immutable_sha256": hash_bytes(canonical(immutable)),
        "scope": {"paths": []},
        "depends-on-work": [],
        "conflicts-with-adrs": [],
        "initial_artifacts": {path: hash_bytes(data) for path, data in sorted(files.items())},
    }
    if migration:
        result["migration"] = migration
    return result



def validate_scope(raw: str) -> list[str]:
    if not isinstance(raw, str) or not raw.strip() or "\n" in raw or "\r" in raw:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-NOT-CLOSED", "scope contains line break or is empty")
    paths = [part.strip() for part in raw.split(",")]
    for path in paths:
        candidate = Path(path)
        if not path or candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts) or "\\" in path:
            raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-NOT-CLOSED", path or raw)
    return paths


def validate_bundle_integrity(bundle: ItemBundle) -> None:
    expected = bundle.metadata.get("initial_artifacts")
    actual = {path: hash_bytes(data) for path, data in sorted(bundle.files.items()) if path != "WORK-ITEM.json"}
    if not isinstance(expected, dict) or expected != actual:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "BUNDLE-INTEGRITY", bundle.work_id)


def validated_hotfix(bundle: ItemBundle) -> dict[str, Any]:
    hotfix = bundle.metadata.get("hotfix")
    if not isinstance(hotfix, dict) or bundle.metadata.get("hotfix_sha256") != hash_bytes(canonical(hotfix)):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "HOTFIX-METADATA-TAMPERED", bundle.work_id)
    if hotfix.get("closed") is not True:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "HOTFIX-INCOMPLETE", bundle.work_id)
    scope = validate_scope(hotfix.get("scope", ""))
    if bundle.metadata.get("scope", {}).get("paths") != scope:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "HOTFIX-SCOPE-DIVERGENCE", bundle.work_id)
    return hotfix


def validate_metadata(metadata: dict[str, Any], expected_work_id: str | None = None) -> dict[str, Any]:
    immutable = metadata.get("immutable")
    if not isinstance(immutable, dict) or metadata.get("immutable_sha256") != hash_bytes(canonical(immutable)):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IMMUTABLE-TAMPERED", expected_work_id or "unknown")
    if (
        immutable.get("schema") != "grill-work-item/v2"
        or not isinstance(immutable.get("work_id"), str)
        or immutable.get("type") not in KINDS
        or not isinstance(immutable.get("slug"), str)
        or not SLUG_RE.fullmatch(immutable["slug"])
        or not WORK_ID_RE.fullmatch(immutable["work_id"])
    ):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "METADATA-SCHEMA", expected_work_id or "unknown")
    if expected_work_id is not None and immutable["work_id"] != expected_work_id:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORK-ID-DIVERGENCE", expected_work_id)
    migration = metadata.get("migration")
    if migration is not None:
        if not isinstance(migration, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "MIGRATION-SCHEMA", immutable["work_id"])
        source_hashes = migration.get("source_hashes")
        source_paths = migration.get("source_paths")
        if (
            not isinstance(source_hashes, dict)
            or not isinstance(source_paths, dict)
            or set(source_hashes) != set(source_paths)
            or not all(isinstance(key, str) and isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for key, value in source_hashes.items())
            or not all(isinstance(key, str) and isinstance(value, str) and value for key, value in source_paths.items())
        ):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "MIGRATION-SCHEMA", immutable["work_id"])
    return immutable


def process_start_observation(pid: int) -> tuple[str, str | None]:
    """Observe Linux process identity without treating read errors as death."""
    if not sys.platform.startswith("linux"):
        return "unsupported", None
    path = Path("/proc") / str(pid) / "stat"
    try:
        fields = path.read_text(encoding="utf-8").rsplit(")", 1)[1].split()
    except FileNotFoundError:
        return "missing", None
    except (OSError, UnicodeError, IndexError):
        return "unavailable", None
    if len(fields) <= 19:
        return "unavailable", None
    return "found", f"linux:{fields[19]}"


def process_start_token(pid: int) -> str | None:
    status, token = process_start_observation(pid)
    return token if status == "found" else None


def stale_local_lock(lock: Path) -> bool:
    try:
        value = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
        pid, host, recorded_start = value.get("pid"), value.get("host"), value.get("process_start")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return False
    observation, current_start = process_start_observation(pid) if type(pid) is int else ("unavailable", None)
    return bool(
        host == socket.gethostname()
        and type(pid) is int
        and pid > 0
        and isinstance(recorded_start, str)
        and recorded_start.startswith("linux:")
        and observation in {"found", "missing"}
        and current_start != recorded_start
    )


def acquire_lock(
    root: Path,
    work_id: str,
    target: Path,
    timeout: float = 15.0,
    *,
    reuse_if_target_exists: bool = False,
) -> Path | None:
    locks = ensure_directory(root, ".grill/locks")
    lock = locks / f"{work_id}.lock"
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock.mkdir()
            owner = {"pid": os.getpid(), "host": socket.gethostname()}
            start_token = process_start_token(os.getpid())
            if start_token is not None:
                owner["process_start"] = start_token
            (lock / "owner.json").write_text(json.dumps(owner, sort_keys=True), encoding="utf-8")
            return lock
        except FileExistsError:
            # Work-item directories are published by one atomic rename. Once the
            # target is visible, readers can safely validate/reuse it without
            # waiting for the creator to remove its diagnostic lock directory.
            if reuse_if_target_exists and target.is_dir() and not target.is_symlink():
                return None
            recovery = locks / f".{work_id}.recovery"
            recovered = False
            try:
                recovery.mkdir()
            except FileExistsError:
                pass
            else:
                try:
                    # Re-read the owner while holding the recovery mutex. This
                    # prevents an old waiter from deleting a newly acquired lock.
                    if stale_local_lock(lock):
                        shutil.rmtree(lock, ignore_errors=False)
                        recovered = True
                except FileNotFoundError:
                    recovered = True
                finally:
                    shutil.rmtree(recovery, ignore_errors=True)
            if recovered:
                continue
            if time.monotonic() >= deadline:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LOCK-CONTENTION", work_id)
            time.sleep(0.03)


def write_bundle_staging(root: Path, work_id: str, metadata: dict[str, Any], files: dict[str, bytes]) -> Path:
    parent = ensure_directory(root, ".grill/work-items")
    staging = Path(tempfile.mkdtemp(prefix=f".{work_id}-", dir=parent))
    try:
        for relative, data in sorted(files.items()):
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        (staging / "docs/adr").mkdir(parents=True, exist_ok=True)
        (staging / "handoffs").mkdir(parents=True, exist_ok=True)
        (staging / "WORK-ITEM.json").write_bytes(
            (json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        )
        return staging
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def rename_child(parent: Path, source: Path, target: Path) -> None:
    """Rename children through a verified directory FD to avoid parent-path substitution."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(parent, flags)
    try:
        parent_stat = os.stat(parent, follow_symlinks=False)
        fd_stat = os.fstat(directory_fd)
        if (fd_stat.st_dev, fd_stat.st_ino) != (parent_stat.st_dev, parent_stat.st_ino):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DIRECTORY-RACE", str(parent))
        os.rename(source.name, target.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
    finally:
        os.close(directory_fd)


def read_local_bundle(root: Path, item: Path) -> ItemBundle:
    reject_symlink_chain(root, item, allow_missing=False)
    if item.is_symlink() or not item.is_dir():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-WORK-ITEM", str(item))
    files: dict[str, bytes] = {}
    for path in sorted(item.rglob("*")):
        if path.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(path))
        if path.is_file():
            relative = path.relative_to(item).as_posix()
            files[relative] = path.read_bytes()
    return bundle_from_files(item.name, files, str(item))


def read_external_bundle(item: Path) -> ItemBundle:
    """Read an artifact root that is intentionally separate from the Git project root."""
    absolute = Path(os.path.abspath(item))
    if Path(os.path.realpath(absolute)) != absolute or absolute.is_symlink() or not absolute.is_dir():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-ARTIFACT-ROOT", str(item))
    files: dict[str, bytes] = {}
    for path in sorted(absolute.rglob("*")):
        if path.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(path))
        if path.is_file():
            files[path.relative_to(absolute).as_posix()] = path.read_bytes()
    raw = files.get("WORK-ITEM.json")
    if raw is None:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-MISSING", str(absolute))
    try:
        metadata = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-INVALID", str(absolute)) from exc
    immutable = validate_metadata(metadata)
    work_id = immutable["work_id"]
    return ItemBundle(work_id, files, str(absolute), bundle_fingerprint(files), metadata)


def bundle_fingerprint(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path, data in sorted(files.items()):
        digest.update(path.encode("utf-8") + b"\0" + hashlib.sha256(data).digest())
    return digest.hexdigest()


def bundle_from_files(work_id: str, files: dict[str, bytes], origin: str) -> ItemBundle:
    raw = files.get("WORK-ITEM.json")
    if raw is None:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-MISSING", origin)
    try:
        metadata = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-INVALID", origin) from exc
    immutable = validate_metadata(metadata, work_id)
    return ItemBundle(work_id, files, origin, bundle_fingerprint(files), metadata)


def init_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if args.type not in KINDS or not SLUG_RE.fullmatch(args.slug):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-IDENTITY", "type or slug invalid")
    work_id = args.work_id or f"{args.type}-{args.slug}-{uuid.uuid4().hex}"
    if not WORK_ID_RE.fullmatch(work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-WORK-ID", work_id)
    target = root / ".grill" / "work-items" / work_id
    lock = acquire_lock(root, work_id, target, reuse_if_target_exists=True)
    try:
        if target.exists():
            bundle = read_local_bundle(root, target)
            immutable = validate_metadata(bundle.metadata, work_id)
            if immutable.get("type") != args.type or immutable.get("slug") != args.slug:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IDENTITY-DIVERGENCE", work_id)
            return {"status": "REUSED", "work_id": work_id, "path": str(target), "fingerprint": bundle.fingerprint}, EXIT_OK
        immutable = immutable_metadata(root, args, work_id)
        files = initial_files(root, work_id, immutable)
        metadata = metadata_document(immutable, files)
        staging = write_bundle_staging(root, work_id, metadata, files)
        try:
            rename_child(target.parent, staging, target)
        except OSError as exc:
            if exc.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
                raise
            shutil.rmtree(staging, ignore_errors=True)
            bundle = read_local_bundle(root, target)
            immutable = validate_metadata(bundle.metadata, work_id)
            if immutable.get("type") != args.type or immutable.get("slug") != args.slug:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IDENTITY-DIVERGENCE", work_id)
            return {"status": "REUSED", "work_id": work_id, "path": str(target), "fingerprint": bundle.fingerprint}, EXIT_OK
        bundle = read_local_bundle(root, target)
        return {"status": "CREATED", "work_id": work_id, "path": str(target), "fingerprint": bundle.fingerprint}, EXIT_OK
    finally:
        if lock is not None:
            shutil.rmtree(lock, ignore_errors=True)



def hotfix_go_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    item = root / ".grill" / "work-items" / args.work_id
    bundle = read_local_bundle(root, item)
    validate_bundle_integrity(bundle)
    hotfix = validated_hotfix(bundle)
    validate_constitution_check(root, bundle.files, bundle.metadata["immutable"].get("constitution", {}))
    command = hotfix.get("test-command")
    if not isinstance(command, str) or not command.strip():
        raise CliFailure(EXIT_NO_GO, "NO-GO", "TEST-COMMAND-MISSING", args.work_id)
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "TEST-COMMAND-INVALID", str(exc)) from exc
    timeout = hotfix.get("test-timeout", 30)
    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-TEST-TIMEOUT", str(timeout))
    try:
        process = subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False, timeout=timeout, shell=False)
        output = ((process.stdout or "") + (process.stderr or ""))[:4096]
        if process.returncode != 0:
            return {"verdict": "NO-GO", "code": "CORRECTION-TEST-FAILED", "returncode": process.returncode, "output": output}, EXIT_NO_GO
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") if isinstance(exc.stdout, str) else "")[:4096]
        return {"verdict": "NO-GO", "code": "CORRECTION-TEST-TIMEOUT", "output": output}, EXIT_NO_GO
    return {"verdict": "HOTFIX-GO", "code": "HOTFIX-GO", "work_id": args.work_id, "test": {"returncode": 0, "output": output}}, EXIT_OK


def audit_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.project_root or args.root)
    item = Path(os.path.abspath(args.artifact_root)) if args.artifact_root else root / ".grill" / "work-items" / args.work_id
    if item.is_dir() and (item / "WORK-ITEM.json").is_file():
        try:
            probe = json.loads((item / "WORK-ITEM.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            probe = {}
        if isinstance(probe, dict) and isinstance(probe.get("hotfix"), dict):
            bundle = read_external_bundle(item) if args.artifact_root else read_local_bundle(root, item)
            try:
                hotfix = validated_hotfix(bundle)
            except CliFailure as failure:
                return {"verdict": failure.verdict, "code": failure.code}, failure.exit_code
            required = ("scope", "reproduction", "evidence", "correction-test", "rollback", "constitution-evidence")
            missing = [key for key in required if not isinstance(hotfix.get(key), str) or not hotfix[key].strip()]
            if missing or hotfix.get("closed") is not True:
                return {"verdict": "NO-GO", "code": "HOTFIX-INCOMPLETE", "missing": missing}, EXIT_NO_GO
            try:
                scope_paths = validate_scope(hotfix["scope"])
            except CliFailure:
                return {"verdict": "NO-GO", "code": "SCOPE-NOT-CLOSED"}, EXIT_NO_GO
            if bundle.metadata.get("scope", {}).get("paths") != scope_paths:
                return {"verdict": "NO-GO", "code": "SCOPE-METADATA-DIVERGENCE"}, EXIT_NO_GO
            try:
                constitutional = validate_constitution_check(root, bundle.files, bundle.metadata["immutable"].get("constitution", {}))
            except CliFailure as failure:
                return {"verdict": "BLOCKED-CONSTITUTION", "code": failure.code}, EXIT_CONSTITUTION
            return {"verdict": "HOTFIX-PREPARED", "code": "HOTFIX-PREPARED", "work_id": bundle.work_id,
                    "scope": hotfix["scope"], "constitutional": constitutional,
                    "post_ship": hotfix.get("post_ship", ["reconcile", "full-document-audit"])}, EXIT_OK
    if not args.artifact_root and not args.work_id:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "--work-id or --artifact-root is required")
    item = Path(os.path.abspath(args.artifact_root)) if args.artifact_root else root / ".grill" / "work-items" / args.work_id
    if not item.is_dir():
        return {"verdict": "NO-GO", "code": "WORK-ITEM-MISSING"}, EXIT_NO_GO
    before = read_external_bundle(item) if args.artifact_root else read_local_bundle(root, item)
    immutable = validate_metadata(before.metadata, before.work_id)
    constitutional = validate_constitution_check(root, before.files, immutable.get("constitution", {}))
    auditor = Path(__file__).with_name("audit_decisions.py")
    process = subprocess.run(
        [sys.executable, str(auditor), str(item), "--project-root", str(root), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        receipt = json.loads(process.stdout.strip())
    except json.JSONDecodeError:
        return {"verdict": "NO-GO", "code": "AUDITOR-INVALID-OUTPUT"}, EXIT_NO_GO
    after = read_external_bundle(item) if args.artifact_root else read_local_bundle(root, item)
    if before.fingerprint != after.fingerprint:
        return {"verdict": "NO-GO", "code": "AUDITOR-MUTATED-WORK-ITEM"}, EXIT_NO_GO
    exit_code = process.returncode if process.returncode in {0, 1, 2, 3} else EXIT_NO_GO
    payload = {
        "verdict": receipt.get("verdict", "NO-GO"),
        "code": receipt.get("code", "OK" if exit_code == 0 else "AUDIT-FAILED"),
        "work_id": before.work_id,
        "constitutional": constitutional,
        "audit": receipt,
    }
    return payload, exit_code


def local_items(root: Path) -> list[ItemBundle]:
    directory = root / ".grill" / "work-items"
    if not directory.exists():
        return []
    reject_symlink_chain(root, directory, allow_missing=False)
    return [read_local_bundle(root, item) for item in sorted(directory.iterdir()) if item.is_dir()]


def ref_items(root: Path, ref: str) -> list[ItemBundle]:
    if not git_optional(root, "rev-parse", "--verify", ref):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-SOURCE-REF", ref)
    output = run_git(root, "ls-tree", "-r", "-z", ref, "--", ".grill/work-items", text=False)
    assert isinstance(output, bytes)
    grouped: dict[str, dict[str, bytes]] = {}
    for record in output.split(b"\0"):
        if not record:
            continue
        header, raw_path = record.split(b"\t", 1)
        mode, object_type, _sha = header.decode("ascii").split()
        path = raw_path.decode("utf-8")
        parts = Path(path).parts
        if len(parts) < 4 or parts[:2] != (".grill", "work-items") or object_type != "blob" or mode == "120000":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-SOURCE-REF", path)
        work_id = parts[2]
        relative = Path(*parts[3:]).as_posix()
        data = run_git(root, "show", f"{ref}:{path}", text=False)
        assert isinstance(data, bytes)
        grouped.setdefault(work_id, {})[relative] = data
    return [bundle_from_files(work_id, files, f"{ref}:{work_id}") for work_id, files in sorted(grouped.items())]


def normalized_scope(metadata: dict[str, Any], work_id: str) -> list[str]:
    scope = metadata.get("scope", {})
    values = scope.get("paths", []) if isinstance(scope, dict) else []
    if not isinstance(values, list):
        raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-SCHEMA", work_id)
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-SCHEMA", work_id)
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-PATH", f"{work_id}:{value}")
        result.append(path.as_posix().rstrip("/"))
    return sorted(set(result))


def scopes_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def scan_qualified_ids(bundle: ItemBundle) -> set[str]:
    ids: set[str] = set()
    for path, data in bundle.files.items():
        if path == "WORK-ITEM.json":
            continue
        name = Path(path).stem
        if ADR_RE.fullmatch(name):
            ids.add(f"{bundle.work_id}/{name}")
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-UTF8", bundle.origin)
        for pattern in (ADR_RE, DQ_RE, BL_RE, PHASE_RE):
            ids.update(f"{bundle.work_id}/{match.group(0)}" for match in pattern.finditer(text))
        if path == "ROUND-LOG.jsonl":
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise CliFailure(EXIT_NO_GO, "NO-GO", "ROUND-LOG-INVALID", bundle.work_id) from exc
                round_id = value.get("round_id")
                if isinstance(round_id, str) and ROUND_RE.fullmatch(round_id):
                    ids.add(f"{bundle.work_id}/{round_id}")
    return ids


def validate_reconciliation(root: Path, bundles: list[ItemBundle]) -> tuple[dict[str, ItemBundle], list[str], list[str]]:
    unique: dict[str, ItemBundle] = {}
    conflicts: list[str] = []
    for bundle in bundles:
        previous = unique.get(bundle.work_id)
        if previous and previous.fingerprint != bundle.fingerprint:
            conflicts.append(f"DUPLICATE-WORK-ID:{bundle.work_id}")
        elif previous is None:
            unique[bundle.work_id] = bundle
    target_constitution, _text, _clauses = constitution_info(root)
    scopes: dict[str, list[str]] = {}
    dependencies: dict[str, list[str]] = {}
    qualified: set[str] = set()
    for work_id, bundle in sorted(unique.items()):
        immutable = validate_metadata(bundle.metadata, work_id)
        recorded = immutable.get("constitution", {})
        if recorded.get("state") != target_constitution.get("state") or recorded.get("sha256") != target_constitution.get("sha256"):
            conflicts.append(f"CONSTITUTION-STALE:{work_id}")
        else:
            try:
                validate_constitution_check(root, bundle.files, recorded)
            except CliFailure as failure:
                conflicts.append(f"CONSTITUTION-CHECK:{work_id}:{failure.code}")
        state_raw = bundle.files.get("state.json")
        try:
            state = json.loads(state_raw.decode("utf-8")) if state_raw else {}
        except (UnicodeError, json.JSONDecodeError):
            state = {}
        if state.get("status") != "complete" or state.get("audit_verdict") != "GO":
            conflicts.append(f"STATE-NOT-RECONCILABLE:{work_id}")
        scopes[work_id] = normalized_scope(bundle.metadata, work_id)
        raw_deps = bundle.metadata.get("depends-on-work", [])
        if not isinstance(raw_deps, list) or not all(isinstance(value, str) for value in raw_deps):
            conflicts.append(f"DEPENDENCY-SCHEMA:{work_id}")
            dependencies[work_id] = []
        else:
            dependencies[work_id] = sorted(set(raw_deps))
        qualified.update(scan_qualified_ids(bundle))
    work_ids = set(unique)
    for work_id, deps in dependencies.items():
        for dependency in deps:
            if dependency not in work_ids:
                conflicts.append(f"DEPENDENCY-MISSING:{work_id}->{dependency}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(work_id: str) -> None:
        if work_id in visiting:
            conflicts.append(f"DEPENDENCY-CYCLE:{work_id}")
            return
        if work_id in visited:
            return
        visiting.add(work_id)
        for dependency in dependencies.get(work_id, []):
            if dependency in work_ids:
                visit(dependency)
        visiting.remove(work_id)
        visited.add(work_id)

    for work_id in sorted(work_ids):
        visit(work_id)
    ordered = sorted(scopes)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            for left_path in scopes[left]:
                for right_path in scopes[right]:
                    if scopes_overlap(left_path, right_path):
                        conflicts.append(f"SCOPE-OVERLAP:{left}:{left_path}<->{right}:{right_path}")
    for work_id, bundle in sorted(unique.items()):
        references = bundle.metadata.get("conflicts-with-adrs", [])
        if not isinstance(references, list):
            conflicts.append(f"ADR-CONFLICT-SCHEMA:{work_id}")
            continue
        for reference in references:
            if not isinstance(reference, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,100}/ADR-\d{4}", reference):
                conflicts.append(f"ADR-CONFLICT-SCHEMA:{work_id}")
            elif reference in qualified:
                conflicts.append(f"ADR-CONFLICT:{work_id}->{reference}")
    return unique, sorted(set(conflicts)), sorted(qualified)


def global_documents(items: dict[str, ItemBundle], qualified: list[str], preview: dict[str, Any]) -> tuple[bytes, bytes]:
    lines = ["# Global ROADMAP", "", "Generated deterministically from reconciled work items.", ""]
    for work_id, bundle in sorted(items.items()):
        immutable = bundle.metadata["immutable"]
        lines.append(f"- **{work_id}** ({immutable['type']}): {immutable['slug']}")
    lines.extend(["", "## Qualified artifact IDs", ""])
    lines.extend(f"- `{value}`" for value in qualified)
    roadmap = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    audit = (
        "# Global Reconciliation Audit\n\n```json\n"
        + json.dumps(preview, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n"
    ).encode("utf-8")
    return roadmap, audit


def dirty_paths(root: Path) -> set[str]:
    output = run_git(root, "status", "--porcelain=v1", "--untracked-files=all", "-z", text=False)
    assert isinstance(output, bytes)
    paths: set[str] = set()
    records = output.split(b"\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        status = record[:2].decode("ascii", "replace")
        value = record[3:].decode("utf-8", "surrogateescape")
        paths.add(value)
        if "R" in status or "C" in status:
            if index < len(records) and records[index]:
                paths.add(records[index].decode("utf-8", "surrogateescape"))
                index += 1
    return paths


def replace_global_directory(root: Path, roadmap: bytes, audit: bytes) -> None:
    grill = ensure_directory(root, ".grill")
    target = grill / "global"
    if target.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(target))
    staging = Path(tempfile.mkdtemp(prefix=".global-", dir=grill))
    backup = grill / f".global-backup-{uuid.uuid4().hex}"
    try:
        (staging / "ROADMAP.md").write_bytes(roadmap)
        (staging / "AUDIT.md").write_bytes(audit)
        if target.exists():
            rename_child(grill, target, backup)
        rename_child(grill, staging, target)
        shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        if target.exists() and backup.exists():
            shutil.rmtree(target, ignore_errors=True)
        if backup.exists() and not target.exists():
            rename_child(grill, backup, target)
        shutil.rmtree(staging, ignore_errors=True)
        raise


def reconcile_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    bundles = local_items(root)
    for source in args.source_root:
        bundles.extend(local_items(project_root(source)))
    for ref in args.source_ref:
        bundles.extend(ref_items(root, ref))
    items, conflicts, qualified = validate_reconciliation(root, bundles)
    preview = {
        "verdict": "NO-GO" if conflicts else "PREVIEW",
        "code": "CONFLICTS" if conflicts else "OK",
        "work_ids": sorted(items),
        "qualified_ids": qualified,
        "conflicts": conflicts,
        "count": len(items),
    }
    if not args.apply:
        return preview, EXIT_NO_GO if conflicts else EXIT_OK
    branch = git_optional(root, "branch", "--show-current")
    if not args.integration_branch or branch != args.integration_branch:
        return {**preview, "verdict": "BLOCKED", "code": "WRONG-INTEGRATION-BRANCH"}, EXIT_BLOCKED
    if conflicts:
        return preview, EXIT_NO_GO
    roadmap, audit = global_documents(items, qualified, preview)
    global_dir = root / ".grill" / "global"
    lock = acquire_lock(root, "global-reconciliation", global_dir)
    try:
        if global_dir.is_dir() and not global_dir.is_symlink():
            current_roadmap = (global_dir / "ROADMAP.md").read_bytes() if (global_dir / "ROADMAP.md").is_file() else None
            current_audit = (global_dir / "AUDIT.md").read_bytes() if (global_dir / "AUDIT.md").is_file() else None
            if current_roadmap == roadmap and current_audit == audit:
                disallowed = dirty_paths(root) - MANAGED_GLOBAL
                disallowed = {path for path in disallowed if not path.startswith(".grill/locks/global-reconciliation.lock/")}
                if disallowed:
                    return {**preview, "verdict": "BLOCKED", "code": "DIRTY-WORKTREE", "dirty": sorted(disallowed)}, EXIT_BLOCKED
                return {**preview, "verdict": "REUSED", "code": "OK"}, EXIT_OK
        dirty = {
            path for path in dirty_paths(root)
            if not path.startswith(".grill/locks/global-reconciliation.lock/") and path not in MANAGED_GLOBAL
        }
        if dirty:
            return {**preview, "verdict": "BLOCKED", "code": "DIRTY-WORKTREE", "dirty": sorted(dirty)}, EXIT_BLOCKED
        replace_global_directory(root, roadmap, audit)
        return {**preview, "verdict": "APPLIED", "code": "OK"}, EXIT_OK
    finally:
        if lock is not None:
            shutil.rmtree(lock, ignore_errors=True)


def collect_legacy(root: Path) -> tuple[dict[str, bytes], dict[str, str]]:
    mapped: dict[str, bytes] = {}
    sources: dict[str, str] = {}

    def add(source: Path, destination: str) -> None:
        reject_symlink_chain(root, source, allow_missing=False)
        if source.is_symlink() or not source.is_file():
            raise CliFailure(EXIT_NO_GO, "NO-GO", "LEGACY-UNSAFE", str(source))
        data = safe_read(source, root=root)
        assert isinstance(data, bytes)
        try:
            data.decode("utf-8")
        except UnicodeError as exc:
            raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-UTF8", str(source)) from exc
        if destination in mapped and mapped[destination] != data:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-CONFLICT", destination)
        mapped[destination] = data
        sources[destination] = source.relative_to(root).as_posix()

    for name in LEGACY_FILES:
        path = root / name
        if path.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-SYMLINK", str(path))
        if path.exists():
            add(path, name)
    for directory_name, destination_name in (("docs/adr", "docs/adr"), ("adrs", "docs/adr"), ("handoffs", "handoffs")):
        directory = root / directory_name
        if directory.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-SYMLINK", directory_name)
        if not directory.exists():
            continue
        reject_symlink_chain(root, directory, allow_missing=False)
        if directory.is_symlink() or not directory.is_dir():
            raise CliFailure(EXIT_NO_GO, "NO-GO", "LEGACY-UNSAFE", directory_name)
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise CliFailure(EXIT_NO_GO, "NO-GO", "LEGACY-SYMLINK", str(path))
            if path.is_file():
                relative = path.relative_to(directory).as_posix()
                add(path, f"{destination_name}/{relative}")
    return mapped, sources


def migrate_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if args.type not in KINDS or not SLUG_RE.fullmatch(args.slug):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-IDENTITY", "type or slug invalid")
    mapped, sources = collect_legacy(root)
    hashes = {path: hash_bytes(data) for path, data in sorted(mapped.items())}
    preview: dict[str, Any] = {"verdict": "PREVIEW", "code": "OK", "map": sources, "hashes": hashes}
    if not args.apply:
        return preview, EXIT_OK
    work_id = args.work_id or f"{args.type}-{args.slug}-migration-{uuid.uuid4().hex}"
    if not WORK_ID_RE.fullmatch(work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-WORK-ID", work_id)
    target = root / ".grill" / "work-items" / work_id
    lock = acquire_lock(root, work_id, target, reuse_if_target_exists=True)
    try:
        if target.exists():
            bundle = read_local_bundle(root, target)
            immutable = validate_metadata(bundle.metadata, work_id)
            if immutable.get("type") != args.type or immutable.get("slug") != args.slug:
                return {**preview, "verdict": "BLOCKED", "code": "IDENTITY-DIVERGENCE", "work_id": work_id}, EXIT_BLOCKED
            migration = bundle.metadata.get("migration", {})
            if migration.get("source_hashes") != hashes:
                return {**preview, "verdict": "BLOCKED", "code": "TARGET-DIVERGES", "work_id": work_id}, EXIT_BLOCKED
            for path, data in mapped.items():
                if path == "state.json":
                    continue
                if bundle.files.get(path) != data:
                    return {**preview, "verdict": "BLOCKED", "code": "TARGET-DIVERGES", "work_id": work_id}, EXIT_BLOCKED
            return {**preview, "verdict": "REUSED", "work_id": work_id}, EXIT_OK
        immutable = immutable_metadata(root, args, work_id)
        files = initial_files(root, work_id, immutable)
        files.update({path: data for path, data in mapped.items() if path != "state.json"})
        metadata = metadata_document(immutable, files, migration={"source_hashes": hashes, "source_paths": sources})
        staging = write_bundle_staging(root, work_id, metadata, files)
        try:
            rename_child(target.parent, staging, target)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return {**preview, "verdict": "APPLIED", "work_id": work_id}, EXIT_OK
    finally:
        if lock is not None:
            shutil.rmtree(lock, ignore_errors=True)


def build_parser() -> JsonParser:
    parser = JsonParser()
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=JsonParser)
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("root")
    init_parser.add_argument("--type", required=True)
    init_parser.add_argument("--slug", required=True)
    init_parser.add_argument("--work-id")
    init_parser.add_argument("--base-ref")
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("root")
    audit_parser.add_argument("--work-id")
    audit_parser.add_argument("--artifact-root")
    audit_parser.add_argument("--project-root")
    reconcile_parser = subparsers.add_parser("reconcile")
    reconcile_parser.add_argument("root")
    reconcile_parser.add_argument("--source-root", action="append", default=[])
    reconcile_parser.add_argument("--source-ref", action="append", default=[])
    reconcile_parser.add_argument("--apply", action="store_true")
    reconcile_parser.add_argument("--integration-branch")
    hotfix_parser = subparsers.add_parser("hotfix")
    hotfix_parser.add_argument("root")
    hotfix_parser.add_argument("--slug", required=True)
    hotfix_parser.add_argument("--scope", required=True)
    hotfix_parser.add_argument("--reproduction", required=True)
    hotfix_parser.add_argument("--evidence", required=True)
    hotfix_parser.add_argument("--correction-test", required=True, dest="correction_test")
    hotfix_parser.add_argument("--rollback", required=True)
    hotfix_parser.add_argument("--constitution-evidence", required=True, dest="constitution_evidence")
    hotfix_parser.add_argument("--test-command", required=True, dest="test_command")
    hotfix_parser.add_argument("--test-timeout", type=int, default=30, dest="test_timeout")
    hotfix_parser.add_argument("--work-id")
    hotfix_parser.add_argument("--base-ref")
    go_parser = subparsers.add_parser("hotfix-go")
    go_parser.add_argument("root")
    go_parser.add_argument("--work-id", required=True)
    migrate_parser = subparsers.add_parser("migrate")
    migrate_parser.add_argument("root")
    migrate_parser.add_argument("--type", required=True)
    migrate_parser.add_argument("--slug", required=True)
    migrate_parser.add_argument("--work-id")
    migrate_parser.add_argument("--base-ref")
    migrate_parser.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        handlers = {
            "init": init_command,
            "audit": audit_command,
            "reconcile": reconcile_command,
            "migrate": migrate_command,
            "hotfix": hotfix_command,
            "hotfix-go": hotfix_go_command,
        }
        payload, exit_code = handlers[args.command](args)
    except CliFailure as failure:
        payload, exit_code = failure.payload(), failure.exit_code
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        payload = {"verdict": "BLOCKED", "code": "UNEXPECTED-INPUT", "error": type(exc).__name__}
        exit_code = EXIT_BLOCKED
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
