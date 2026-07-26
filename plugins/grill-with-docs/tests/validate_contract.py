#!/usr/bin/env python3
"""Deterministic packaging and fail-closed auditor checks."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills/grill-with-docs"
manifest_path = next(path for path in [PLUGIN / ".codex-plugin/plugin.json", PLUGIN / ".claude-plugin/plugin.json"] if path.is_file())
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["name"] == "grill-with-docs" and manifest["version"] == "1.1.0"
for rel in [
    "SKILL.md", "references/session-protocol.md", "references/upstream-attribution.md",
    "assets/CONTEXT.template.md", "assets/ADR.template.md", "assets/DECISION-BACKLOG.template.md",
    "assets/DECISION-FRONTIER.template.md", "assets/ROADMAP.template.md", "assets/AUDIT.template.md",
    "assets/PHASE-SPECIFY-HANDOFF.template.md", "assets/PLAN-CONTEXT.template.md",
    "assets/state.template.json", "assets/ROUND-LOG.template.jsonl", "scripts/audit_decisions.py",
]:
    assert (SKILL / rel).is_file(), rel
text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
for term in [
    "EVIDENCE GAP", "docs/adr", "BL-NNNN", "DQ-NNNN", "ROUND-LOG.jsonl", "FASE-NNN",
    "SAFETY_STOP", "PAUSED_USER", "COMPLETE + NO-GO", "context-refs", "specify-handoff",
]:
    assert term in text, term

script = SKILL / "scripts/audit_decisions.py"
fixtures = PLUGIN / "tests/fixtures"

def run(root: Path, expected: int) -> None:
    result = subprocess.run([sys.executable, str(script), str(root)], text=True, capture_output=True)
    assert result.returncode == expected, (root.name, result.stdout, result.stderr)
    expected_verdict = "GO" if expected == 0 else "NO-GO"
    assert expected_verdict in result.stdout.splitlines(), (root.name, result.stdout)

for fixture, expected in [("valid", 0), ("invalid-schema", 1), ("invalid-cycle", 1), ("invalid-deferred", 1)]:
    run(fixtures / fixture, expected)

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary) / "project"
    shutil.copytree(fixtures / "valid", root)

    roadmap = root / "ROADMAP.md"
    roadmap.write_text(roadmap.read_text(encoding="utf-8").replace("context-refs: Tenant, API", "context-refs: Inexistente"), encoding="utf-8")
    run(root, 1)

    shutil.rmtree(root)
    shutil.copytree(fixtures / "valid", root)
    roadmap = root / "ROADMAP.md"
    roadmap.write_text(roadmap.read_text(encoding="utf-8").replace("## FASE-001 —", "## FASE 001 —"), encoding="utf-8")
    run(root, 1)

    shutil.rmtree(root)
    shutil.copytree(fixtures / "valid", root)
    (root / "handoffs/FASE-001-SPECIFY-HANDOFF.md").unlink()
    run(root, 1)

    shutil.rmtree(root)
    shutil.copytree(fixtures / "valid", root)
    frontier = root / "DECISION-FRONTIER.md"
    frontier.write_text(frontier.read_text(encoding="utf-8").replace("confirmar limite tenant fornecedor", "escolher contrato api fornecedor"), encoding="utf-8")
    run(root, 1)

    shutil.rmtree(root)
    shutil.copytree(fixtures / "valid", root)
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    state["status"] = "safety-stop"
    (root / "state.json").write_text(json.dumps(state), encoding="utf-8")
    run(root, 1)

    shutil.rmtree(root)
    shutil.copytree(fixtures / "valid", root)
    (root / "ROUND-LOG.jsonl").write_text("not-json\n", encoding="utf-8")
    run(root, 1)

    shutil.rmtree(root)
    shutil.copytree(fixtures / "valid", root)
    log = root / "ROUND-LOG.jsonl"
    log.write_text(log.read_text(encoding="utf-8").replace('"R-0002"', '"R-0001"'), encoding="utf-8")
    run(root, 1)

root = PLUGIN.parents[1]
marketplace_path = next(path for path in [root / ".agents/plugins/marketplace.json", root / ".claude-plugin/marketplace.json"] if path.is_file())
marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
entry = next(item for item in marketplace["plugins"] if item["name"] == "grill-with-docs")
if "source" in entry and isinstance(entry["source"], dict):
    assert entry["source"] == {"source": "local", "path": "./plugins/grill-with-docs"}
else:
    assert entry["source"] == "./plugins/grill-with-docs"
readme = (root / "README.md").read_text(encoding="utf-8")
assert "`grill-with-docs`" in readme and "ROADMAP por fases" in readme and "SAFETY_STOP" in readme
print("validate_contract: PASS")
