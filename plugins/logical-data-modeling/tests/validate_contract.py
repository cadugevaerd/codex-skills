#!/usr/bin/env python3
"""Validate the portable logical-data-modeling plugin contract."""
import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "logical-data-modeling" / "SKILL.md"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"

required = (
    "name: logical-data-modeling",
    "Modo: transacional-relacional",
    "Modo: analitico-bi",
    "Modo: oltp-para-analitico",
    "Não gere, execute ou aplique DDL",
    "grão",
    "Governança e segurança",
    "Aprovação antes da implementação física",
    "HTML único e autocontido",
    "<!doctype html>",
    "<style>",
    "<script>",
    "prefers-reduced-motion",
    "Expandir seções",
    "Foco de leitura",
    "innerHTML",
)
text = SKILL.read_text(encoding="utf-8")
assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
assert all(item in text for item in required), "missing required safety or modeling contract"
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
assert manifest["name"] == "logical-data-modeling"
assert manifest["skills"] == "./skills/"
print("logical-data-modeling Codex contract: OK")
