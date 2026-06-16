#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_item(repo: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo": repo.get("name"),
        "repo_path": repo.get("path"),
        "id": item.get("id"),
        "title": item.get("title") or item.get("name") or "Item sem titulo",
        "description": item.get("notes") or item.get("description") or item.get("detail") or "",
        "type": item.get("type", "item"),
        "status": item.get("status", "aberto"),
        "priority": item.get("priority") or item.get("severity") or "media",
        "rank": item.get("rank"),
        "agent": item.get("agent"),
        "source": item.get("source") or "backlog",
        "updated": item.get("updated") or item.get("created"),
        "raw": item,
    }


def collect_repo(repo: dict[str, Any]) -> dict[str, Any]:
    repo_path = Path(str(repo.get("path", ""))).expanduser()
    backlog_path = repo_path / str(repo.get("backlog_path", ".specify/backlog.json"))
    result: dict[str, Any] = {
        "repo": repo.get("name"),
        "path": str(repo_path),
        "backlog_path": str(backlog_path),
        "ok": False,
        "items": [],
        "error": None,
    }
    if not repo.get("enabled", True):
        result["error"] = "repositorio desabilitado"
        return result
    if not backlog_path.exists():
        result["error"] = "backlog nao encontrado"
        return result
    try:
        data = read_json(backlog_path)
        raw_items = data.get("items", []) if isinstance(data, dict) else []
        result["items"] = [
            normalize_item(repo, item)
            for item in raw_items
            if item.get("status") not in {"resolvido", "descartado"}
        ]
        result["ok"] = True
        result["updated"] = data.get("updated") if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    return result


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        config = default_config()
        write_json(path, config)
        print(f"Configuracao criada automaticamente: {path}", file=sys.stderr)
        return config
    return read_json(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta backlogs dos repositorios configurados")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--out", default="-", help="Arquivo JSON de saida ou '-' para stdout")
    parser.add_argument("--repo", action="append", help="Filtra por nome de repo; pode repetir")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    config = load_config(Path(args.config).expanduser())
    repos = [repo for repo in config.get("repos", []) if repo.get("enabled", True)]
    if args.repo:
        wanted = set(args.repo)
        repos = [repo for repo in repos if repo.get("name") in wanted]

    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(collect_repo, repo): repo for repo in repos}
        for future in as_completed(futures):
            results.append(future.result())

    all_items = [item for result in results for item in result.get("items", [])]
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": str(Path(args.config).expanduser()),
        "repos": sorted(results, key=lambda value: str(value.get("repo"))),
        "items": all_items,
        "summary": {
            "repos_total": len(repos),
            "repos_ok": sum(1 for result in results if result.get("ok")),
            "items_total": len(all_items),
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.out == "-":
        print(text, end="")
    else:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Backlogs coletados: {out}")


if __name__ == "__main__":
    main()
