#!/usr/bin/env python3
"""Read-only SessionStart/SubagentStart project-context hook."""
import json
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).with_name("quality_gatectl.py")


def main():
    try:
        payload = json.load(sys.stdin)
        raw = payload.get("cwd") if isinstance(payload, dict) else None
        if not isinstance(raw, str) or not raw.startswith("/") or "\0" in raw:
            raise ValueError("missing or malformed cwd")
        cwd = Path(raw)
        if not cwd.is_dir():
            raise ValueError("cwd is not a directory")
        probe = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
        if probe.returncode != 0 or not probe.stdout.strip():
            raise ValueError("cwd is not inside a Git repository")
        root = Path(probe.stdout.strip()).resolve()
        plan = subprocess.run(
            [sys.executable, str(CLI), "plan", "--root", str(root), "--json"],
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        if plan.returncode not in (0, 2):
            raise ValueError("quality-gate plan failed")
        data = json.loads(plan.stdout)
        snapshot = data.get("snapshot", {}).get("fingerprint")
        risk = data.get("risk", {}).get("profile")
        gates = data.get("required_gates")
        tasks = data.get("investigator_tasks")
        if not isinstance(snapshot, str) or len(snapshot) != 64 or risk not in {"P1", "P2", "P3"} or not isinstance(gates, list) or len(tasks or []) != 12:
            raise ValueError("quality-gate plan is invalid or incomplete")
        context = (
            f"root={root}; quality-gate=v2; state=read-only; "
            f"snapshot={snapshot}; risk={risk}; required-gates={','.join(gates)}; "
            "modules=MOD-001..MOD-012; next=fan-out exactly one read-only investigator per module"
        )
        output = {"hookSpecificOutput": {"additionalContext": context}}
    except Exception as exc:
        output = {"hookSpecificOutput": {"additionalContext": "quality-gate BLOCKED: " + str(exc)}}
    print(json.dumps(output, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    main()
