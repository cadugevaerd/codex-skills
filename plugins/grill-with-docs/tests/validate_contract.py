#!/usr/bin/env python3
"""Deterministic packaging and fail-closed auditor checks."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills/grill-with-docs"
manifest_path = next(path for path in [PLUGIN / ".codex-plugin/plugin.json", PLUGIN / ".claude-plugin/plugin.json"] if path.is_file())
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["name"] == "grill-with-docs" and manifest["version"] == "1.0.0"
for rel in [
    "SKILL.md", "references/session-protocol.md", "references/upstream-attribution.md",
    "assets/CONTEXT.template.md", "assets/ADR.template.md", "assets/DECISION-BACKLOG.template.md",
    "assets/ROADMAP.template.md", "assets/AUDIT.template.md", "scripts/audit_decisions.py",
]:
    assert (SKILL / rel).is_file(), rel
text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
for term in ["EVIDENCE GAP", "docs/adr", "BL-NNNN", "impact scan", "ROADMAP", "GO", "NO-GO", "BLOCKED", "STOP", "custo"]:
    assert term in text, term

script = SKILL / "scripts/audit_decisions.py"
for fixture, expected in [("valid", 0), ("invalid-schema", 1), ("invalid-cycle", 1), ("invalid-deferred", 1)]:
    result = subprocess.run([sys.executable, str(script), str(PLUGIN / "tests/fixtures" / fixture)], text=True, capture_output=True)
    assert result.returncode == expected, (fixture, result.stdout, result.stderr)
    assert ("GO" if expected == 0 else "NO-GO") in result.stdout, (fixture, result.stdout)

root = PLUGIN.parents[1]
marketplace_path = next(path for path in [root / ".agents/plugins/marketplace.json", root / ".claude-plugin/marketplace.json"] if path.is_file())
marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
entry = next(item for item in marketplace["plugins"] if item["name"] == "grill-with-docs")
if "source" in entry and isinstance(entry["source"], dict):
    assert entry["source"] == {"source": "local", "path": "./plugins/grill-with-docs"}
else:
    assert entry["source"] == "./plugins/grill-with-docs"
readme = (root / "README.md").read_text(encoding="utf-8")
assert "`grill-with-docs`" in readme and "grill-with-docs" in readme
print("validate_contract: PASS")
