#!/usr/bin/env python3
"""Codex CLI marketplace/install smoke test for caveman-stable.

Requires Codex CLI 0.146.0 or newer. This is intentionally separate from the
stdlib-only deterministic contract test.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ID = "caveman-stable@codex-skills"
SOURCES = ("startup", "resume", "clear", "compact")


def run(command: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
    if result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def main() -> None:
    codex = os.environ.get("CODEX_BIN") or shutil.which("codex")
    assert codex, "Codex CLI not found; set CODEX_BIN"

    version = run([codex, "--version"], env=os.environ.copy()).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="caveman-codex-smoke-") as directory:
        env = os.environ.copy()
        env["CODEX_HOME"] = directory

        run([codex, "plugin", "marketplace", "add", str(REPO_ROOT), "--json"], env=env)
        installed = json.loads(run([codex, "plugin", "add", PLUGIN_ID, "--json"], env=env).stdout)
        assert installed["pluginId"] == PLUGIN_ID
        assert installed["version"] == "1.0.0"

        plugin_root = Path(installed["installedPath"])
        assert plugin_root.is_dir()
        hooks = json.loads((plugin_root / "hooks/hooks.json").read_text(encoding="utf-8"))
        session = hooks["hooks"]["SessionStart"]
        assert len(session) == 1
        assert session[0]["matcher"] == "startup|resume|clear|compact"
        handler = session[0]["hooks"][0]
        assert handler["command"] == 'python3 "${PLUGIN_ROOT}/hooks/inject_context.py"'
        assert handler["commandWindows"] == 'py -3 "%PLUGIN_ROOT%\\hooks\\inject_context.py"'

        expected = (plugin_root / "skills/caveman-stable/references/output-contract.md").read_text(
            encoding="utf-8"
        )
        hook_env = env.copy()
        hook_env["PLUGIN_ROOT"] = str(plugin_root)
        for source in SOURCES:
            payload = json.dumps(
                {
                    "session_id": "codex-cli-smoke",
                    "hook_event_name": "SessionStart",
                    "source": source,
                }
            )
            result = subprocess.run(
                [sys.executable, str(plugin_root / "hooks/inject_context.py")],
                input=payload,
                text=True,
                capture_output=True,
                env=hook_env,
                check=False,
            )
            assert result.returncode == 0, (source, result.stderr)
            output = json.loads(result.stdout)["hookSpecificOutput"]
            assert output["hookEventName"] == "SessionStart"
            assert output["additionalContext"] == expected

    print(f"caveman-stable Codex CLI smoke: OK ({version})")


if __name__ == "__main__":
    main()
