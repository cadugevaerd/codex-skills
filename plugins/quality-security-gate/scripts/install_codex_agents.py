#!/usr/bin/env python3
"""Safely install/uninstall Quality Security Gate V2 Codex agents."""
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

OWNER = "quality-security-gate"
BEGIN = "# BEGIN quality-security-gate plugin agents"
END = "# END quality-security-gate plugin agents"
MARKER = ".quality-security-gate-managed.json"
AGENTS = {
    f"quality_security_gate_mod_{i:03d}": f"quality-security-gate-mod-{i:03d}.toml"
    for i in range(1, 13)
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def pattern() -> re.Pattern[str]:
    return re.compile(rf"(?ms)^\s*{re.escape(BEGIN)}.*?{re.escape(END)}\s*(?:\n|$)")


def strip_block(content: str) -> str:
    return pattern().sub("", content).rstrip()


def marker_hash(content: str) -> str | None:
    match = re.search(
        rf"{re.escape(BEGIN)}.*?^# marker_sha256 = \"([0-9a-f]{{64}})\"$.*?{re.escape(END)}",
        content,
        re.M | re.S,
    )
    return match.group(1) if match else None


def block(hash_value: str) -> str:
    lines = [BEGIN, f'# marker_sha256 = "{hash_value}"']
    for role, filename in AGENTS.items():
        lines.extend([
            f"[agents.{role}]",
            f'description = "Investigador read-only {role[-7:].upper().replace("_", "-")}."',
            f'config_file = "agents/{filename}"',
            "",
        ])
    lines.append(END)
    return "\n".join(lines)


def reject_path(path: Path, label: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"{label} não pode ser symlink: {path}")
    if path.exists() and not path.is_file():
        raise RuntimeError(f"{label} deve ser arquivo regular: {path}")


def reject_conflicts(unmanaged: str) -> None:
    conflicts = [role for role in AGENTS if re.search(rf"(?m)^\s*\[agents\.{re.escape(role)}\]\s*$", unmanaged)]
    if conflicts:
        raise RuntimeError("roles preexistentes fora do bloco gerenciado: " + ", ".join(conflicts))


def source_payload(plugin_root: Path, codex_home: Path) -> tuple[dict[str, str], dict[str, bytes]]:
    source_agents = plugin_root / "agents"
    rendered: dict[str, str] = {}
    home = codex_home.as_posix().replace('"', '\\"')
    for filename in AGENTS.values():
        source = source_agents / filename
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"agent fonte ausente ou inseguro: {source}")
        rendered[filename] = source.read_text(encoding="utf-8").replace("__CODEX_HOME__", home)

    knowledge: dict[str, bytes] = {}
    for directory in ("skills", "references", "schemas"):
        root = plugin_root / directory
        if not root.is_dir() or root.is_symlink():
            raise RuntimeError(f"bundle obrigatório ausente ou inseguro: {root}")
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise RuntimeError(f"bundle contém symlink: {path}")
            if path.is_file():
                knowledge[path.relative_to(plugin_root).as_posix()] = path.read_bytes()
    return rendered, knowledge


def validate_managed(codex_home: Path, current: str) -> dict | None:
    agents_dir = codex_home / "agents"
    knowledge_dir = agents_dir / "quality-security-gate-knowledge"
    has_block = BEGIN in current or END in current
    if not knowledge_dir.exists():
        if has_block or any((agents_dir / name).exists() for name in AGENTS.values()):
            raise RuntimeError("estado parcial ou não gerenciado detectado")
        return None
    if knowledge_dir.is_symlink() or not knowledge_dir.is_dir() or not has_block:
        raise RuntimeError("diretório gerenciado ou bloco inválido")
    marker = knowledge_dir / MARKER
    if not marker.is_file() or marker.is_symlink():
        raise RuntimeError("marker de ownership ausente ou inseguro")
    expected_marker_hash = marker_hash(current)
    if expected_marker_hash is None or file_sha(marker) != expected_marker_hash:
        raise RuntimeError("marker não corresponde ao bloco gerenciado")
    metadata = json.loads(marker.read_text(encoding="utf-8"))
    if metadata.get("owner") != OWNER or set(metadata.get("agents", {})) != set(AGENTS.values()):
        raise RuntimeError("ownership ou inventário de agents inválido")
    if not isinstance(metadata.get("knowledge"), dict):
        raise RuntimeError("inventário de conhecimento inválido")
    for filename, expected in metadata["agents"].items():
        target = agents_dir / filename
        reject_path(target, f"agent {filename}")
        if not target.is_file() or file_sha(target) != expected:
            raise RuntimeError(f"agent gerenciado alterado: {filename}")
    actual_files = {
        path.relative_to(knowledge_dir).as_posix()
        for path in knowledge_dir.rglob("*")
        if path.is_file() and path.name != MARKER
    }
    if actual_files != set(metadata["knowledge"]):
        raise RuntimeError("árvore de conhecimento divergiu")
    for relative, expected in metadata["knowledge"].items():
        path = knowledge_dir / relative
        if path.is_symlink() or file_sha(path) != expected:
            raise RuntimeError(f"conhecimento gerenciado alterado: {relative}")
    return metadata


def install(plugin_root: Path, codex_home: Path) -> None:
    config = codex_home / "config.toml"
    backup = codex_home / "config.toml.bak-quality-security-gate"
    agents_dir = codex_home / "agents"
    knowledge_dir = agents_dir / "quality-security-gate-knowledge"
    codex_home.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    reject_path(config, "config.toml")
    reject_path(backup, "backup")
    current = config.read_text(encoding="utf-8") if config.exists() else ""
    managed = validate_managed(codex_home, current)
    unmanaged = strip_block(current)
    reject_conflicts(unmanaged)
    rendered, knowledge = source_payload(plugin_root, codex_home)

    stage = Path(tempfile.mkdtemp(prefix=".quality-security-gate-stage-", dir=agents_dir))
    try:
        for relative, content in knowledge.items():
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        metadata = {
            "owner": OWNER,
            "format": 1,
            "agents": {name: sha(content.encode("utf-8")) for name, content in rendered.items()},
            "knowledge": {name: sha(content) for name, content in knowledge.items()},
        }
        marker_content = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
        atomic_write(stage / MARKER, marker_content)
        for filename, content in rendered.items():
            atomic_write(agents_dir / filename, content)
        if managed is not None:
            old = knowledge_dir.with_name(knowledge_dir.name + ".old")
            if old.exists():
                raise RuntimeError(f"backup transitório preexistente: {old}")
            os.replace(knowledge_dir, old)
            try:
                os.replace(stage, knowledge_dir)
            except Exception:
                os.replace(old, knowledge_dir)
                raise
            shutil.rmtree(old)
        else:
            os.replace(stage, knowledge_dir)
        if config.exists() and not backup.exists():
            shutil.copy2(config, backup)
        marker_digest = file_sha(knowledge_dir / MARKER)
        new_content = unmanaged + ("\n\n" if unmanaged else "") + block(marker_digest) + "\n"
        atomic_write(config, new_content)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(f"OK: 12 agentes read-only instalados em {agents_dir}")


def uninstall(codex_home: Path) -> None:
    config = codex_home / "config.toml"
    agents_dir = codex_home / "agents"
    knowledge_dir = agents_dir / "quality-security-gate-knowledge"
    reject_path(config, "config.toml")
    current = config.read_text(encoding="utf-8") if config.exists() else ""
    managed = validate_managed(codex_home, current)
    if managed is None:
        print("OK: agentes já ausentes")
        return
    atomic_write(config, strip_block(current) + ("\n" if strip_block(current) else ""))
    for filename in AGENTS.values():
        (agents_dir / filename).unlink()
    shutil.rmtree(knowledge_dir)
    print("OK: agentes Quality Security Gate removidos")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    plugin_root = Path(__file__).resolve().parents[1]
    try:
        home = args.codex_home.expanduser().resolve()
        uninstall(home) if args.uninstall else install(plugin_root, home)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
