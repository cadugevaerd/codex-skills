#!/usr/bin/env python3
"""Validate grillme-langgraph's mirror contract and required decision paths."""
from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
plugin = root / "plugins/grillme-langgraph"
skill = plugin / "skills/grillme-langgraph"
required = {
    "SKILL.md": ["Fase 0 — Gate de adequação", "SEM LANGGRAPH", "USO PARCIAL", "LANGGRAPH JUSTIFICADO", "recomendo rodar o grill sem LangGraph"],
    "references/padrao-langgraph.md": ["quando **não** usar LangGraph", "LangGraph **não** fornece serialização"],
    "assets/template-sem-langgraph.md": ["SEM LANGGRAPH", "Idempotency key", "futura fronteira LangGraph"],
    "assets/exemplo-uso-parcial-timbro.md": ["USO PARCIAL", "SEM LANGGRAPH", "LANGGRAPH JUSTIFICADO"],
}
for rel, tokens in required.items():
    content = (skill / rel).read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in content]
    assert not missing, f"{rel}: missing {missing}"
for manifest in plugin.glob(".*/plugin.json"):
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["version"] == "1.1.0", manifest
print("OK: local grillme-langgraph contract")
