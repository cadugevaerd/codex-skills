#!/usr/bin/env python3
"""Install/uninstall LangGraph Architecture custom agents for Codex safely."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any

OWNER = "langgraph-architecture"
MARKER_NAME = ".langgraph-architecture-managed.json"
MARKER_FORMAT = 1
BEGIN = "# BEGIN langgraph-architecture plugin agents"
BEGIN_JOINED = "# BEGIN langgraph-architecture plugin agents (original-no-final-newline)"
END = "# END langgraph-architecture plugin agents"
AGENTS = {
    "langgraph_architect": "langgraph-architect.toml",
    "langgraph_reviewer": "langgraph-reviewer.toml",
}
BLOCK_BODY = '''[agents.langgraph_architect]
description = "Cria planos verificáveis de arquitetura LangGraph em contexto isolado e read-only."
config_file = "agents/langgraph-architect.toml"

[agents.langgraph_reviewer]
description = "Audita repositórios LangGraph em contexto isolado e read-only."
config_file = "agents/langgraph-reviewer.toml"'''


def managed_pattern(begin: str, include_separator: bool = False) -> re.Pattern[str]:
    prefix = r"\n" if include_separator else ""
    return re.compile(rf"{prefix}{re.escape(begin)}.*?{re.escape(END)}\n?", re.S)


def has_managed_block(content: str) -> bool:
    return BEGIN in content or BEGIN_JOINED in content


def extract_marker_hash(content: str) -> str | None:
    for begin in (BEGIN_JOINED, BEGIN):
        match = re.search(rf"{re.escape(begin)}(?P<body>.*?){re.escape(END)}", content, re.S)
        if match:
            hash_match = re.search(r'(?m)^# marker_sha256 = "([0-9a-f]{64})"$', match.group("body"))
            return hash_match.group(1) if hash_match else None
    return None


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


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def reject_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"{label} não pode ser symlink: {path}")


def assert_regular_or_absent(path: Path, label: str) -> None:
    reject_symlink(path, label)
    if path.exists() and not path.is_file():
        raise RuntimeError(f"{label} deve ser arquivo regular: {path}")


def assert_no_unmanaged_conflict(content: str) -> None:
    conflicts = [
        role for role in AGENTS
        if re.search(rf"(?m)^\s*\[agents\.{re.escape(role)}(?:\.|\])", content)
    ]
    if conflicts:
        raise RuntimeError("roles já existentes fora do bloco gerenciado: " + ", ".join(conflicts))


def expected_tree_entries(files: list[str]) -> set[str]:
    entries = {MARKER_NAME, *files}
    for filename in files:
        parent = Path(filename).parent
        while parent != Path("."):
            entries.add(parent.as_posix())
            parent = parent.parent
    return entries


def load_ownership(
    knowledge_dir: Path,
    agents_dir: Path,
    expected_marker_hash: str | None,
) -> dict[str, Any] | None:
    reject_symlink(knowledge_dir, "diretório de conhecimento")
    if not knowledge_dir.exists():
        return None
    if not knowledge_dir.is_dir():
        raise RuntimeError(f"caminho de conhecimento não é diretório: {knowledge_dir}")

    marker = knowledge_dir / MARKER_NAME
    reject_symlink(marker, "marker de ownership")
    if not marker.is_file():
        raise RuntimeError(f"diretório preexistente não gerenciado; marker ausente: {knowledge_dir}")
    if expected_marker_hash is None or sha256_file(marker) != expected_marker_hash:
        raise RuntimeError("integridade do marker não confere com o bloco gerenciado")
    try:
        metadata = json.loads(marker.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"marker de ownership inválido: {exc}") from exc
    if metadata.get("owner") != OWNER or metadata.get("format") != MARKER_FORMAT:
        raise RuntimeError("marker pertence a outro owner ou formato")

    agent_files = metadata.get("agent_files")
    knowledge_files = metadata.get("knowledge_files")
    if not isinstance(agent_files, dict) or set(agent_files) != set(AGENTS.values()):
        raise RuntimeError("inventário de agents no marker é inválido")
    if not isinstance(knowledge_files, dict) or not all(
        isinstance(item, str) and isinstance(file_hash, str)
        for item, file_hash in knowledge_files.items()
    ):
        raise RuntimeError("inventário de conhecimento no marker é inválido")
    if any(Path(item).is_absolute() or ".." in Path(item).parts or not item.startswith("skills/") for item in knowledge_files):
        raise RuntimeError("marker contém caminho de conhecimento inseguro")

    actual_entries: set[str] = set()
    for path in knowledge_dir.rglob("*"):
        reject_symlink(path, "entrada gerenciada")
        actual_entries.add(path.relative_to(knowledge_dir).as_posix())
    expected_entries = expected_tree_entries(list(knowledge_files))
    if actual_entries != expected_entries:
        extra = sorted(actual_entries - expected_entries)
        missing = sorted(expected_entries - actual_entries)
        raise RuntimeError(f"diretório gerenciado divergiu; extras={extra} ausentes={missing}")

    for filename, expected_hash in knowledge_files.items():
        knowledge_file = knowledge_dir / filename
        if not knowledge_file.is_file() or sha256_file(knowledge_file) != expected_hash:
            raise RuntimeError(f"arquivo de conhecimento gerenciado foi alterado: {knowledge_file}")

    for filename, expected_hash in agent_files.items():
        destination = agents_dir / filename
        assert_regular_or_absent(destination, f"agent {filename}")
        if not destination.is_file():
            raise RuntimeError(f"agent gerenciado ausente: {destination}")
        if not isinstance(expected_hash, str) or sha256_file(destination) != expected_hash:
            raise RuntimeError(f"agent gerenciado foi alterado: {destination}")
    return metadata


def render_payload(plugin_root: Path, codex_home: Path) -> tuple[dict[str, str], dict[str, Any], Path]:
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
    for source in [*required_agents, *source_skills.rglob("*")]:
        if source.is_symlink():
            raise RuntimeError(f"payload fonte contém symlink: {source}")

    rendered_home = codex_home.as_posix().replace('"', '\\"')
    rendered_agents = {
        source.name: source.read_text(encoding="utf-8").replace("__CODEX_HOME__", rendered_home)
        for source in required_agents
    }
    knowledge_files = {
        f"skills/{path.relative_to(source_skills).as_posix()}": sha256_file(path)
        for path in sorted(source_skills.rglob("*")) if path.is_file()
    }
    metadata: dict[str, Any] = {
        "owner": OWNER,
        "format": MARKER_FORMAT,
        "agent_files": {
            filename: sha256_bytes(content.encode("utf-8"))
            for filename, content in rendered_agents.items()
        },
        "knowledge_files": knowledge_files,
    }

    agents_dir = codex_home / "agents"
    stage = Path(tempfile.mkdtemp(prefix=".langgraph-architecture-stage-", dir=agents_dir))
    try:
        shutil.copytree(source_skills, stage / "skills")
        atomic_write(stage / MARKER_NAME, json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return rendered_agents, metadata, stage


def replace_knowledge(knowledge_dir: Path, stage: Path, managed_before: bool) -> None:
    if not managed_before:
        os.replace(stage, knowledge_dir)
        return
    backup = Path(tempfile.mkdtemp(prefix=".langgraph-architecture-old-", dir=knowledge_dir.parent))
    backup.rmdir()
    os.replace(knowledge_dir, backup)
    try:
        os.replace(stage, knowledge_dir)
    except Exception:
        os.replace(backup, knowledge_dir)
        raise
    shutil.rmtree(backup)


def install(plugin_root: Path, codex_home: Path) -> None:
    config = codex_home / "config.toml"
    backup_config = codex_home / "config.toml.bak-langgraph-architecture"
    agents_dir = codex_home / "agents"
    knowledge_dir = agents_dir / "langgraph-architecture-knowledge"

    codex_home.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    assert_regular_or_absent(config, "config.toml")
    assert_regular_or_absent(backup_config, "backup config.toml")

    original = config.read_text(encoding="utf-8") if config.exists() else ""
    managed_block = has_managed_block(original)
    current_marker_hash = extract_marker_hash(original)
    ownership = load_ownership(knowledge_dir, agents_dir, current_marker_hash)
    if ownership is None:
        if managed_block:
            raise RuntimeError("bloco gerenciado existe sem marker de ownership")
        for filename in AGENTS.values():
            destination = agents_dir / filename
            reject_symlink(destination, f"agent {filename}")
            if destination.exists():
                raise RuntimeError(f"agent preexistente não gerenciado: {destination}")
    elif not managed_block:
        raise RuntimeError("marker de ownership existe sem bloco gerenciado")

    unmanaged = remove_managed_block(original)
    assert_no_unmanaged_conflict(unmanaged)
    rendered_agents, _metadata, stage = render_payload(plugin_root, codex_home)
    new_marker_hash = sha256_file(stage / MARKER_NAME)

    if config.exists() and not backup_config.exists():
        shutil.copy2(config, backup_config)
    try:
        for filename, rendered in rendered_agents.items():
            atomic_write(agents_dir / filename, rendered)
        replace_knowledge(knowledge_dir, stage, managed_before=ownership is not None)
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

    joined = bool(unmanaged) and not unmanaged.endswith("\n")
    begin = BEGIN_JOINED if joined else BEGIN
    separator = "\n" if joined else ""
    new_content = (
        unmanaged + separator + begin + "\n"
        + f'# marker_sha256 = "{new_marker_hash}"\n'
        + BLOCK_BODY + "\n" + END + "\n"
    )
    atomic_write(config, new_content)
    print(f"OK: agents instalados em {agents_dir}")
    print("MODELS: architect=gpt-5.6/max reviewer=gpt-5.6/max")


def uninstall(codex_home: Path) -> None:
    config = codex_home / "config.toml"
    agents_dir = codex_home / "agents"
    knowledge_dir = agents_dir / "langgraph-architecture-knowledge"
    assert_regular_or_absent(config, "config.toml")

    original = config.read_text(encoding="utf-8") if config.exists() else ""
    managed_block = has_managed_block(original)
    current_marker_hash = extract_marker_hash(original)
    ownership = load_ownership(knowledge_dir, agents_dir, current_marker_hash)
    unmanaged_agent_exists = any((agents_dir / filename).exists() or (agents_dir / filename).is_symlink() for filename in AGENTS.values())
    if ownership is None:
        if managed_block or unmanaged_agent_exists:
            raise RuntimeError("estado parcial ou não gerenciado; uninstall recusado")
        print(f"OK: agents LangGraph Architecture já ausentes de {codex_home}")
        return
    if not managed_block:
        raise RuntimeError("marker de ownership existe sem bloco gerenciado")

    if config.exists():
        atomic_write(config, remove_managed_block(original))
    for filename in AGENTS.values():
        (agents_dir / filename).unlink()
    shutil.rmtree(knowledge_dir)
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
