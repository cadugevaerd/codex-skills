#!/usr/bin/env python3
"""Deterministic packaging, hook, and fail-closed checks for caveman-stable."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]
HOOK = PLUGIN_ROOT / "hooks/inject_context.py"
CONTRACT = PLUGIN_ROOT / "skills/caveman-stable/references/output-contract.md"
SHARED_MANIFEST = PLUGIN_ROOT / "tests/shared-files.sha256"
SOURCES = ("startup", "resume", "clear", "compact")


def run_hook(payload: object, *, root: Path | None = PLUGIN_ROOT, raw: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if root is None:
        env.pop("PLUGIN_ROOT", None)
    else:
        env["PLUGIN_ROOT"] = str(root)
    input_text = raw if raw is not None else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def valid_payload(source: str) -> dict[str, str]:
    return {
        "session_id": "test-session",
        "hook_event_name": "SessionStart",
        "source": source,
    }


def assert_failed(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr.startswith("caveman-stable:")


def verify_shared_files() -> None:
    for line in SHARED_MANIFEST.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        payload = (PLUGIN_ROOT / relative).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == digest, relative


def main() -> None:
    expected = CONTRACT.read_text(encoding="utf-8")
    for source in SOURCES:
        result = run_hook(valid_payload(source))
        assert result.returncode == 0, (source, result.stderr)
        assert result.stderr == ""
        output = json.loads(result.stdout)
        hook_output = output["hookSpecificOutput"]
        assert hook_output["hookEventName"] == "SessionStart"
        assert hook_output["additionalContext"] == expected

    assert_failed(run_hook({}, raw="{"))
    assert_failed(run_hook([]))
    assert_failed(run_hook({"hook_event_name": "SessionStart"}))
    assert_failed(run_hook({"hook_event_name": "Stop", "source": "startup"}))
    assert_failed(run_hook(valid_payload("unsupported")))
    assert_failed(run_hook(valid_payload("startup"), root=None))

    with tempfile.TemporaryDirectory() as directory:
        empty_root = Path(directory)
        assert_failed(run_hook(valid_payload("startup"), root=empty_root))
        empty_contract = empty_root / "skills/caveman-stable/references/output-contract.md"
        empty_contract.parent.mkdir(parents=True)
        empty_contract.write_text("", encoding="utf-8")
        assert_failed(run_hook(valid_payload("startup"), root=empty_root))

    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    hooks = json.loads((PLUGIN_ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
    marketplace = json.loads((REPO_ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "caveman-stable"
    assert manifest["version"] == "1.0.0"
    assert manifest["skills"] == "./skills/"
    assert manifest["hooks"] == "./hooks/hooks.json"
    assert manifest["interface"]["displayName"] == "Caveman Stable"

    entries = [item for item in marketplace["plugins"] if item["name"] == "caveman-stable"]
    assert len(entries) == 1
    assert entries[0]["version"] == manifest["version"]
    assert entries[0]["source"] == {"source": "local", "path": "./plugins/caveman-stable"}

    assert list(hooks["hooks"]) == ["SessionStart"]
    session_hook = hooks["hooks"]["SessionStart"]
    assert len(session_hook) == 1
    assert session_hook[0]["matcher"] == "startup|resume|clear|compact"
    command = session_hook[0]["hooks"][0]["command"]
    assert command == 'python3 "${PLUGIN_ROOT}/hooks/inject_context.py"'
    assert not any(path.name == "state.json" for path in PLUGIN_ROOT.rglob("*"))

    verify_shared_files()
    assert (PLUGIN_ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License\n")
    upstream = (PLUGIN_ROOT / "UPSTREAM.md").read_text(encoding="utf-8")
    assert "JuliusBrussee/caveman" in upstream
    assert "0d95a81d35a9f2d123a5e9430d1cfc43d55f1bb0" in upstream

    package_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in PLUGIN_ROOT.rglob("*")
        if path.is_file() and path.suffix in {".md", ".json"}
    )
    assert ("Her" + "mes") not in package_text
    assert ("UserPrompt" + "Submit") not in package_text

    readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "codex plugin marketplace add cadugevaerd/codex-skills --ref main",
        "codex plugin add caveman-stable@codex-skills",
        "/hooks",
        "compact",
        "desinstale",
    ):
        assert phrase.lower() in readme, phrase

    print("caveman-stable Codex contract: OK")


if __name__ == "__main__":
    main()
