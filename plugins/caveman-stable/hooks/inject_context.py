#!/usr/bin/env python3
"""Emit Caveman Stable developer context for Codex SessionStart hooks."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ALLOWED_SOURCES = {"startup", "resume", "clear", "compact"}
CONTRACT_RELATIVE_PATH = Path("skills/caveman-stable/references/output-contract.md")


def fail(message: str) -> int:
    print(f"caveman-stable: {message}", file=sys.stderr)
    return 1


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return fail("invalid JSON hook input")

    if not isinstance(payload, dict):
        return fail("hook input must be a JSON object")
    if payload.get("hook_event_name") != "SessionStart":
        return fail("unexpected hook event")
    if payload.get("source") not in ALLOWED_SOURCES:
        return fail("unsupported or missing SessionStart source")

    plugin_root = os.environ.get("PLUGIN_ROOT")
    if not plugin_root:
        return fail("PLUGIN_ROOT is not set")

    contract_path = Path(plugin_root) / CONTRACT_RELATIVE_PATH
    try:
        context = contract_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return fail("output contract is unavailable")
    if not context.strip():
        return fail("output contract is empty")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    json.dump(output, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
