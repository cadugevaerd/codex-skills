#!/usr/bin/env python3
"""Deterministic contract and packaging checks for code-debug."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "code-debug"
SKILL_PATH = PLUGIN_ROOT / "skills" / "code-debug" / "SKILL.md"
FIXTURES = PLUGIN_ROOT / "tests" / "fixtures"
MARKER = "Diagnóstico encerrado. Nenhuma correção foi executada."
REPORT_HEADINGS = [
    "## Status",
    "## Sintoma reproduzido",
    "## Evidências",
    "## Caminho de investigação/Hipóteses eliminadas",
    "## Causa raiz",
    "## Cadeia causal",
    "## Arquivos envolvidos",
    "## Limitações/incertezas",
]


def require(text: str, values: list[str], source: Path) -> None:
    for value in values:
        assert value in text, f"missing {value!r} in {source}"


def forbid(text: str, values: list[str], source: Path) -> None:
    for value in values:
        assert value not in text, f"forbidden {value!r} in {source}"


def load_json(path: Path) -> dict:
    assert path.is_file(), f"required JSON missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def section_body(lines: list[str], heading: str) -> str:
    start = lines.index(heading) + 1
    end = next(
        (
            index
            for index in range(start, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    return "\n".join(lines[start:end]).strip()


def validate_report(path: Path, expected_status: str, confirmed: bool) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    positions: list[int] = []
    for heading in REPORT_HEADINGS:
        assert lines.count(heading) == 1, f"heading must occur once: {heading!r} in {path}"
        positions.append(lines.index(heading))
    assert positions == sorted(positions), f"headings out of order in {path}"

    status = section_body(lines, "## Status")
    assert status == expected_status, f"unexpected status in {path}: {status!r}"

    cause = section_body(lines, "## Causa raiz")
    evidence = section_body(lines, "## Evidências")
    chain = section_body(lines, "## Cadeia causal")
    files = section_body(lines, "## Arquivos envolvidos")
    assert evidence and chain and files, f"empty required section in {path}"

    if confirmed:
        assert cause and "não comprovada" not in cause.lower(), path
        assert "src/config.py" in files, "confirmed fixture needs an exact source location"
        assert "teste mínimo isolado" in evidence, "confirmed fixture needs objective verification"
    else:
        assert cause == "Causa raiz não comprovada ainda.", path
        assert "não pode ser fechada" in chain.lower(), path

    forbidden_headings = [
        "## Sugestão de fix",
        "## Sugestao de fix",
        "## Verificação recomendada",
        "## Verificacao recomendada",
    ]
    forbid(text, forbidden_headings, path)
    assert text.count(MARKER) == 1, f"marker must occur once in {path}"
    assert text.rstrip().endswith(MARKER), f"marker must end {path}"


def assert_no_fix_promise(value: str, source: object) -> None:
    lowered = value.lower()
    assert not re.search(r"\bfix\b", lowered), source
    assert not re.search(r"\bsugest(?:ao|ão)\b", lowered), source


def validate_manifest(path: Path) -> None:
    data = load_json(path)
    assert data["version"] == "1.1.0", path
    assert "diagn" in data["description"].lower(), path
    assert_no_fix_promise(data["description"], path)

    interface = data.get("interface", {})
    for field in ("shortDescription", "longDescription"):
        if field in interface:
            assert_no_fix_promise(interface[field], (path, field))


skill = SKILL_PATH.read_text(encoding="utf-8")
require(
    skill,
    [
        "diagnose-only",
        "reproduzir → coletar evidências → testar hipóteses → concluir → relatório → STOP",
        "Correção exige nova solicitação ou outro workflow.",
        "não aplicar patch de produto",
        "não validar fix",
        "não criar commit, PR ou backlog",
        "não sugerir comandos de correção",
        "preservando a sujeira preexistente",
        "causa raiz não comprovada ainda",
        MARKER,
    ],
    SKILL_PATH,
)
forbid(
    skill,
    [
        "Prefira corrigir a causa raiz",
        "## Sugestão de fix",
        "## Sugestao de fix",
        "## Verificação recomendada",
        "## Verificacao recomendada",
        "Se aplicar o fix estiver no escopo",
    ],
    SKILL_PATH,
)

validate_report(
    FIXTURES / "root-cause-report.example.md",
    "Causa raiz comprovada.",
    confirmed=True,
)
validate_report(
    FIXTURES / "inconclusive-report.example.md",
    "Causa raiz não comprovada ainda.",
    confirmed=False,
)

codex_manifest = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
claude_manifest = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
codex_marketplace = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
claude_marketplace = REPO_ROOT / ".claude-plugin" / "marketplace.json"

if codex_marketplace.is_file():
    validate_manifest(codex_manifest)
    entries = load_json(codex_marketplace)["plugins"]
    entry = next(item for item in entries if item["name"] == "code-debug")
    assert entry["source"]["path"] == "./plugins/code-debug"
elif claude_marketplace.is_file():
    validate_manifest(claude_manifest)
    entry = next(
        item
        for item in load_json(claude_marketplace)["plugins"]
        if item["name"] == "code-debug"
    )
    assert entry["version"] == "1.1.0"
    assert "diagn" in entry["description"].lower()
    assert_no_fix_promise(entry["description"], claude_marketplace)
else:
    raise AssertionError("unable to determine Codex or Claude plugin runtime")

readme_path = REPO_ROOT / "README.md"
readme = readme_path.read_text(encoding="utf-8")
table_lines = [line for line in readme.splitlines() if "`code-debug`" in line]
assert table_lines, "README must document code-debug"
assert any("diagn" in line.lower() and "sem" in line.lower() for line in table_lines)
assert "/code-debug" in readme, "README must include a code-debug invocation"
assert "nova solicitação ou outro workflow" in readme, "README must state the stop boundary"

print(f"OK code-debug contract: {REPO_ROOT}")
