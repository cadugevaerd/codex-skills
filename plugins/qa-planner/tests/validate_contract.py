#!/usr/bin/env python3
"""Deterministic contract and packaging checks for qa-planner."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "qa-planner"
SKILL_PATH = PLUGIN_ROOT / "skills" / "qa-planner" / "SKILL.md"
TEMPLATE_PATH = PLUGIN_ROOT / "skills" / "qa-planner" / "assets" / "QA.template.md"
FIXTURE_PATH = PLUGIN_ROOT / "tests" / "fixtures" / "QA.example.md"
MARKER_START = "<!-- qa-planner:start -->"
MARKER_END = "<!-- qa-planner:end -->"
TERMINAL_MARKER = "Planejamento de QA encerrado. Nenhum teste foi executado."
HEADINGS = [
    "## 1. Identificação",
    "## 2. Evidências consultadas",
    "## 3. Requisitos e critérios de aceite",
    "## 4. Rastreabilidade",
    "## 5. Escopo e fora de escopo",
    "## 6. Estratégia de testes",
    "## 7. Ambiente, dados e dependências",
    "## 8. Cenários detalhados",
    "## 9. Regressão necessária",
    "## 10. Candidatos à automação",
    "## 11. Dúvidas, suposições e bloqueios",
    "## 12. Handoff para a IA executora",
]


def load_json(path: Path) -> dict:
    assert path.is_file(), f"required JSON missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def require(text: str, values: list[str], source: Path) -> None:
    for value in values:
        assert value in text, f"missing {value!r} in {source}"


def validate_document(path: Path, fixture: bool = False) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# QA Plan\n"), path
    assert text.count(MARKER_START) == 1, path
    assert text.count(MARKER_END) == 1, path
    assert text.index(MARKER_START) < text.index(MARKER_END), path
    positions = []
    for heading in HEADINGS:
        assert text.count(heading) == 1, f"heading must occur once: {heading!r} in {path}"
        positions.append(text.index(heading))
    assert positions == sorted(positions), path
    assert text.count(TERMINAL_MARKER) == 1, path
    assert text.index(TERMINAL_MARKER) < text.index(MARKER_END), path
    if fixture:
        assert "### QA-001" in text and "### QA-002" in text, path
        assert "**Status inicial:** NOT_RUN" in text, path
        assert "REQ-001" in text and "RISK-001" in text, path
        assert "**Status final:**" not in text, path
        assert "**Resultado da execução:**" not in text, path
        assert "QA-RESULTS.md" in text, path


def validate_manifest(path: Path) -> None:
    data = load_json(path)
    assert data["name"] == "qa-planner", path
    assert data["version"] == "1.0.0", path
    description = data["description"].lower()
    assert "qa" in description and "sem executar" in description, path


skill = SKILL_PATH.read_text(encoding="utf-8")
require(
    skill,
    [
        "plan-only",
        "validar escopo → analisar requisitos → planejar testes → criar cenários → gravar QA.md → STOP",
        "Nunca execute testes, builds, linters, typecheckers",
        "A única escrita permitida no repositório-alvo é o bloco gerenciado de `QA.md`",
        "QA-RESULTS.md",
        MARKER_START,
        MARKER_END,
        TERMINAL_MARKER,
        "Status inicial:** NOT_RUN",
    ],
    SKILL_PATH,
)
validate_document(TEMPLATE_PATH)
validate_document(FIXTURE_PATH, fixture=True)

codex_manifest = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
claude_manifest = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
codex_marketplace = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
claude_marketplace = REPO_ROOT / ".claude-plugin" / "marketplace.json"

if codex_marketplace.is_file():
    validate_manifest(codex_manifest)
    entry = next(item for item in load_json(codex_marketplace)["plugins"] if item["name"] == "qa-planner")
    assert entry["source"]["path"] == "./plugins/qa-planner", entry
elif claude_marketplace.is_file():
    validate_manifest(claude_manifest)
    entry = next(item for item in load_json(claude_marketplace)["plugins"] if item["name"] == "qa-planner")
    assert entry["source"] == "./plugins/qa-planner", entry
    assert entry["version"] == "1.0.0", entry
else:
    raise AssertionError("unable to determine Codex or Claude plugin runtime")

readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
assert "`qa-planner`" in readme, "README must document qa-planner"
assert "/qa-planner" in readme, "README must include a qa-planner invocation"
assert "QA.md" in readme and "sem executar testes" in readme.lower(), "README must state the boundary"

print(f"OK qa-planner contract: {REPO_ROOT}")
