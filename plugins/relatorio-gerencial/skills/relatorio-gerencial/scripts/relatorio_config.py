#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".claude" / "relatorio-gerencial.json"

DEFAULT_REPOS = [
    {
        "name": "masterai-agents-backend",
        "path": "/home/caraujo/projetos/masterai-agents-backend",
        "owner": "master-ai",
        "enabled": True,
        "backlog_path": ".specify/backlog.json",
        "description": "Backend dos agentes MasterAI",
    },
    {
        "name": "librechat-private",
        "path": "/home/caraujo/projetos/librechat-private",
        "owner": "master-ai",
        "enabled": True,
        "backlog_path": ".specify/backlog.json",
        "description": "Projeto master-ai / LibreChat privado",
    },
    {
        "name": "master-agents",
        "path": "/home/caraujo/projetos/master-agents",
        "owner": "master-ai",
        "enabled": True,
        "backlog_path": ".specify/backlog.json",
        "description": "Repositorio master-agents",
    },
    {
        "name": "proxy-cm-ai",
        "path": "/home/caraujo/projetos/proxy-cm-ai",
        "owner": "master-ai",
        "enabled": True,
        "backlog_path": ".specify/backlog.json",
        "description": "Proxy CM AI",
    },
]


def default_config() -> dict[str, Any]:
    return {
        "version": 1,
        "updated": date.today().isoformat(),
        "repos": DEFAULT_REPOS,
        "report": {
            "language": "pt-BR",
            "audience": "gerente",
            "tone": "nao-tecnico",
            "format": "one-page-pdf",
            "max_groups": 5,
        },
    }


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_config()
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config["updated"] = date.today().isoformat()
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def repo_index(config: dict[str, Any], name: str) -> int | None:
    for idx, repo in enumerate(config.get("repos", [])):
        if repo.get("name") == name:
            return idx
    return None


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.config).expanduser()
    if path.exists() and not args.force:
        print(f"Configuracao ja existe: {path}")
        return
    config = default_config()
    save_config(path, config)
    print(f"Configuracao criada: {path}")


def cmd_list(args: argparse.Namespace) -> None:
    config = load_config(Path(args.config).expanduser())
    for repo in config.get("repos", []):
        status = "on" if repo.get("enabled", True) else "off"
        print(f"{status:3} {repo.get('name')} -> {repo.get('path')} ({repo.get('backlog_path', '.specify/backlog.json')})")


def cmd_add(args: argparse.Namespace) -> None:
    path = Path(args.config).expanduser()
    config = load_config(path)
    idx = repo_index(config, args.name)
    repo = {
        "name": args.name,
        "path": str(Path(args.path).expanduser()),
        "owner": args.owner,
        "enabled": not args.disabled,
        "backlog_path": args.backlog_path,
        "description": args.description or args.name,
    }
    if idx is None:
        config.setdefault("repos", []).append(repo)
        action = "adicionado"
    else:
        config["repos"][idx].update(repo)
        action = "atualizado"
    save_config(path, config)
    print(f"Repositorio {action}: {args.name}")


def cmd_remove(args: argparse.Namespace) -> None:
    path = Path(args.config).expanduser()
    config = load_config(path)
    before = len(config.get("repos", []))
    config["repos"] = [repo for repo in config.get("repos", []) if repo.get("name") != args.name]
    save_config(path, config)
    print(f"Repositorio removido: {args.name}" if len(config["repos"]) != before else f"Repositorio nao encontrado: {args.name}")


def set_enabled(args: argparse.Namespace, enabled: bool) -> None:
    path = Path(args.config).expanduser()
    config = load_config(path)
    idx = repo_index(config, args.name)
    if idx is None:
        raise SystemExit(f"Repositorio nao encontrado: {args.name}")
    config["repos"][idx]["enabled"] = enabled
    save_config(path, config)
    print(f"Repositorio {'habilitado' if enabled else 'desabilitado'}: {args.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gerencia ~/.claude/relatorio-gerencial.json")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Caminho do JSON de configuracao global")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Cria configuracao global com repos padrao")
    p_init.add_argument("--force", action="store_true", help="Sobrescreve configuracao existente")
    p_init.set_defaults(func=cmd_init)

    p_list = sub.add_parser("list", help="Lista repositorios configurados")
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="Adiciona ou atualiza repositorio")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--path", required=True)
    p_add.add_argument("--owner", default="master-ai")
    p_add.add_argument("--backlog-path", default=".specify/backlog.json")
    p_add.add_argument("--description", default="")
    p_add.add_argument("--disabled", action="store_true")
    p_add.set_defaults(func=cmd_add)

    p_remove = sub.add_parser("remove", help="Remove repositorio")
    p_remove.add_argument("--name", required=True)
    p_remove.set_defaults(func=cmd_remove)

    p_disable = sub.add_parser("disable", help="Desabilita repositorio sem remover")
    p_disable.add_argument("--name", required=True)
    p_disable.set_defaults(func=lambda args: set_enabled(args, False))

    p_enable = sub.add_parser("enable", help="Habilita repositorio")
    p_enable.add_argument("--name", required=True)
    p_enable.set_defaults(func=lambda args: set_enabled(args, True))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
