#!/usr/bin/env python3
"""Install/uninstall LangSmith Evals custom agents for Codex.

Codex plugins currently auto-discover skills, not custom-agent role registrations.
This idempotent installer copies the role configs and manages one marked block in
$CODEX_HOME/config.toml (default: ~/.codex/config.toml).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

BEGIN = "# BEGIN langsmith-evals plugin agents"
END = "# END langsmith-evals plugin agents"
AGENT_NAMES = (
    "langsmith_evals_engineer",
    "langsmith_pytest_engineer",
    "langsmith_evals_auditor",
)
BLOCK = f"""{BEGIN}
[agents.langsmith_evals_engineer]
description = "Implementa datasets, evaluators, experiments, backtests e gates LangSmith-first."
config_file = "agents/langsmith-evals-engineer.toml"

[agents.langsmith_pytest_engineer]
description = "Implementa e executa Pytest para contratos deterministicos, sem LLM-as-judge."
config_file = "agents/langsmith-pytest-engineer.toml"

[agents.langsmith_evals_auditor]
description = "Audita evidencias LangSmith de forma independente e emite GO, NO-GO ou BLOCKED."
config_file = "agents/langsmith-evals-auditor.toml"
{END}"""


def managed_pattern() -> re.Pattern[str]:
    return re.compile(
        rf"(?ms)^\s*{re.escape(BEGIN)}.*?{re.escape(END)}\s*(?:\n|$)"
    )


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def remove_managed_block(content: str) -> str:
    return managed_pattern().sub("", content).rstrip() + ("\n" if content.strip() else "")


def assert_no_unmanaged_conflict(content_without_block: str) -> None:
    conflicts = [
        name
        for name in AGENT_NAMES
        if re.search(rf"(?m)^\s*\[agents\.{re.escape(name)}\]\s*$", content_without_block)
    ]
    if conflicts:
        names = ", ".join(conflicts)
        raise RuntimeError(
            f"config.toml ja possui secoes nao gerenciadas para: {names}. "
            "Renomeie/remova essas secoes ou nao use o instalador."
        )


def install(plugin_root: Path, codex_home: Path) -> None:
    config = codex_home / "config.toml"
    agents_dir = codex_home / "agents"
    knowledge_dir = agents_dir / "langsmith-evals-knowledge"
    source_agents = plugin_root / "agents"
    source_skill = plugin_root / "skills" / "langsmith-evals"

    agent_sources = [
        source_agents / "langsmith-evals-engineer.toml",
        source_agents / "langsmith-pytest-engineer.toml",
        source_agents / "langsmith-evals-auditor.toml",
    ]
    required = [
        *agent_sources,
        source_skill / "SKILL.md",
        source_skill / "references" / "patterns.md",
        source_skill / "references" / "audit-checklist.md",
        source_skill / "references" / "pytest-deterministic.md",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Arquivos obrigatorios ausentes:\n- " + "\n- ".join(missing))

    current = config.read_text(encoding="utf-8") if config.exists() else ""
    unmanaged = remove_managed_block(current)
    assert_no_unmanaged_conflict(unmanaged)

    codex_home.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    for source in agent_sources:
        shutil.copy2(source, agents_dir / source.name)

    if knowledge_dir.exists():
        shutil.rmtree(knowledge_dir)
    shutil.copytree(source_skill, knowledge_dir)

    if config.exists() and not (codex_home / "config.toml.bak-langsmith-evals").exists():
        shutil.copy2(config, codex_home / "config.toml.bak-langsmith-evals")

    new_content = unmanaged.rstrip()
    if new_content:
        new_content += "\n\n"
    new_content += BLOCK + "\n"
    atomic_write(config, new_content)

    print(f"OK: agentes instalados em {agents_dir}")
    print(f"OK: conhecimento instalado em {knowledge_dir}")
    print(f"OK: papeis registrados em {config}")
    print(
        "MODELS: engineer=gpt-5.6-terra "
        "pytest=gpt-5.6-terra auditor=gpt-5.6-terra"
    )


def uninstall(codex_home: Path) -> None:
    config = codex_home / "config.toml"
    agents_dir = codex_home / "agents"
    if config.exists():
        current = config.read_text(encoding="utf-8")
        atomic_write(config, remove_managed_block(current))
    for name in (
        "langsmith-evals-engineer.toml",
        "langsmith-pytest-engineer.toml",
        "langsmith-evals-auditor.toml",
    ):
        path = agents_dir / name
        if path.exists():
            path.unlink()
    knowledge = agents_dir / "langsmith-evals-knowledge"
    if knowledge.exists():
        shutil.rmtree(knowledge)
    print(f"OK: agentes LangSmith Evals removidos de {codex_home}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Diretorio Codex; padrao: $CODEX_HOME ou ~/.codex",
    )
    parser.add_argument("--uninstall", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plugin_root = Path(__file__).resolve().parents[1]
    try:
        if args.uninstall:
            uninstall(args.codex_home.expanduser().resolve())
        else:
            install(plugin_root, args.codex_home.expanduser().resolve())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
