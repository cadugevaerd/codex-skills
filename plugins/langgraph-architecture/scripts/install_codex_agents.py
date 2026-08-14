#!/usr/bin/env python3
"""Install/uninstall LangGraph Architecture custom agents for Codex."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

BEGIN = "# BEGIN langgraph-architecture plugin agents"
BEGIN_JOINED = "# BEGIN langgraph-architecture plugin agents (original-no-final-newline)"
END = "# END langgraph-architecture plugin agents"
AGENTS = {
    "langgraph_architect": "langgraph-architect.toml",
    "langgraph_reviewer": "langgraph-reviewer.toml",
}
BLOCK_BODY = '''[agents.langgraph_architect]
description = "Cria planos verificáveis de arquitetura LangGraph em contexto isolado."
config_file = "agents/langgraph-architect.toml"

[agents.langgraph_reviewer]
description = "Audita repositórios LangGraph em contexto isolado e read-only."
config_file = "agents/langgraph-reviewer.toml"'''


def managed_pattern(begin: str, include_separator: bool = False) -> re.Pattern[str]:
    prefix = r"\n" if include_separator else ""
    return re.compile(rf"{prefix}{re.escape(begin)}.*?{re.escape(END)}\n?", re.S)


def remove_managed_block(content: str) -> str:
    content = managed_pattern(BEGIN_JOINED, include_separator=True).sub("", content)
    return managed_pattern(BEGIN).sub("", content)


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


def assert_no_unmanaged_conflict(content: str) -> None:
    conflicts = [
        role for role in AGENTS
        if re.search(rf"(?m)^\s*\[agents\.{re.escape(role)}\]\s*$", content)
    ]
    if conflicts:
        raise RuntimeError("roles já existentes fora do bloco gerenciado: " + ", ".join(conflicts))


def install(plugin_root: Path, codex_home: Path) -> None:
    config = codex_home / "config.toml"
    agents_dir = codex_home / "agents"
    knowledge_dir = agents_dir / "langgraph-architecture-knowledge"
    source_agents = plugin_root / "agents"
    source_skills = plugin_root / "skills"
    required_agents = [source_agents / filename for filename in AGENTS.values()]
    required_skills = [
        source_skills / "langgraph-architecture-plan" / "SKILL.md",
        source_skills / "langgraph-architecture-plan" / "assets" / "LANGGRAPH-ARCHITECTURE-PLAN.example.md",
        source_skills / "langgraph-repository-review" / "SKILL.md",
        source_skills / "langgraph-repository-review" / "assets" / "LANGGRAPH-REVIEW.example.md",
    ]
    missing = [str(path) for path in [*required_agents, *required_skills] if not path.is_file()]
    if missing:
        raise RuntimeError("arquivos obrigatórios ausentes:\n- " + "\n- ".join(missing))

    original = config.read_text(encoding="utf-8") if config.exists() else ""
    unmanaged = remove_managed_block(original)
    assert_no_unmanaged_conflict(unmanaged)

    codex_home.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    if config.exists() and not (codex_home / "config.toml.bak-langgraph-architecture").exists():
        shutil.copy2(config, codex_home / "config.toml.bak-langgraph-architecture")

    rendered_home = codex_home.as_posix().replace('"', '\\"')
    for source in required_agents:
        rendered = source.read_text(encoding="utf-8").replace("__CODEX_HOME__", rendered_home)
        atomic_write(agents_dir / source.name, rendered)
    if knowledge_dir.exists():
        shutil.rmtree(knowledge_dir)
    shutil.copytree(source_skills, knowledge_dir / "skills")

    joined = bool(unmanaged) and not unmanaged.endswith("\n")
    begin = BEGIN_JOINED if joined else BEGIN
    separator = "\n" if joined else ""
    new_content = unmanaged + separator + begin + "\n" + BLOCK_BODY + "\n" + END + "\n"
    atomic_write(config, new_content)
    print(f"OK: agents instalados em {agents_dir}")
    print("MODELS: architect=gpt-5.6/max reviewer=gpt-5.6/max")


def uninstall(codex_home: Path) -> None:
    config = codex_home / "config.toml"
    agents_dir = codex_home / "agents"
    if config.exists():
        atomic_write(config, remove_managed_block(config.read_text(encoding="utf-8")))
    for filename in AGENTS.values():
        path = agents_dir / filename
        if path.exists():
            path.unlink()
    knowledge = agents_dir / "langgraph-architecture-knowledge"
    if knowledge.exists():
        shutil.rmtree(knowledge)
    print(f"OK: agents LangGraph Architecture removidos de {codex_home}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--codex-home", type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Diretório Codex; padrão: $CODEX_HOME ou ~/.codex",
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
    except (OSError, RuntimeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
