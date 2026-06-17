#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from typing import Any

import relatorio_config

CONFIG_PATH = Path.home() / ".claude" / "relatorio-gerencial.json"
GLOBAL_BACKLOG = Path.home() / ".backlog" / "backlog.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_global_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo": item.get("repo"),
        "repo_path": item.get("repo_path"),
        "id": item.get("id"),
        "title": item.get("title") or "Item sem titulo",
        "description": item.get("notes") or item.get("detail") or "",
        "type": item.get("type", "item"),
        "status": item.get("status", "aberto"),
        "priority": item.get("priority") or "media",
        "rank": item.get("rank"),
        "agent": item.get("agent"),
        "source": item.get("source") or "backlog",
        "updated": item.get("updated") or item.get("created"),
        "raw": item,
    }


def collect_global(path: Path, repo_filter: set[str] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Le o backlog GLOBAL unico (~/.backlog/backlog.json) e agrupa por repo,
    devolvendo o mesmo shape (results, all_items) do modo per-projeto."""
    data = read_json(path)
    raw_items = data.get("items", []) if isinstance(data, dict) else []
    items = [
        normalize_global_item(item)
        for item in raw_items
        if item.get("status") not in {"resolvido", "descartado"}
        and (not repo_filter or item.get("repo") in repo_filter)
    ]
    by_repo: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_repo.setdefault(str(item.get("repo")), []).append(item)
    results: list[dict[str, Any]] = []
    for repo, ritems in sorted(by_repo.items(), key=lambda kv: kv[0]):
        results.append({
            "repo": repo,
            "path": ritems[0].get("repo_path") if ritems else None,
            "backlog_path": str(path),
            "source": str(path),
            "ok": True,
            "items": ritems,
            "error": None,
            "updated": data.get("updated") if isinstance(data, dict) else None,
        })
    return results, items


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


def read_local_backlog(repo: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    path = Path(str(repo.get("path", ""))).expanduser()
    backlog_rel = str(repo.get("backlog_path", ".specify/backlog.json"))
    if not path.exists():
        return None, None
    backlog_path = path / backlog_rel
    if not backlog_path.exists():
        return None, str(backlog_path)
    return read_json(backlog_path), str(backlog_path)


def read_remote_backlog(repo: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    owner = str(repo.get("owner") or "").strip()
    name = str(repo.get("name") or "").strip()
    if not owner or not name:
        return None, None

    branch = str(repo.get("branch", "main"))
    backlog_rel = str(repo.get("backlog_path", ".specify/backlog.json")).lstrip("/")
    url = str(repo.get("raw_backlog_url") or f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/{backlog_rel}")
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8")), url
    except Exception as exc:
        return {"_error": str(exc), "_error_type": type(exc).__name__}, url


def collect_repo(repo: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "repo": repo.get("name"),
        "path": str(Path(str(repo.get("path", ""))).expanduser()),
        "backlog_path": str(repo.get("backlog_path", ".specify/backlog.json")),
        "source": "backlog",
        "ok": False,
        "items": [],
        "error": None,
    }

    if not repo.get("enabled", True):
        result["error"] = "repositorio desabilitado"
        return result

    backlog_data: dict[str, Any] | None
    source_ref: str | None

    backlog_data, source_ref = read_local_backlog(repo)
    if backlog_data is None and source_ref:
        result["source"] = source_ref
    if backlog_data is None:
        backlog_data, source_ref = read_remote_backlog(repo)
        result["source"] = source_ref or ""

    if backlog_data is None:
        result["error"] = "backlog nao encontrado"
        return result
    if isinstance(backlog_data, dict) and backlog_data.get("_error"):
        result["error"] = f"falha ao buscar backlog remoto: {backlog_data.get('_error')}"
        return result

    try:
        raw_items = backlog_data.get("items", []) if isinstance(backlog_data, dict) else []
        result["items"] = [
            normalize_item(repo, item)
            for item in raw_items
            if item.get("status") not in {"resolvido", "descartado"}
        ]
        result["ok"] = True
        result["updated"] = backlog_data.get("updated") if isinstance(backlog_data, dict) else None
    except Exception as exc:  # noqa: BLE001
        # Erro controlado para não interromper a coleta dos outros repos.
        result["error"] = str(exc)
    return result


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        config = relatorio_config.default_config()
        relatorio_config.save_config(path, config)
        print(f"Configuracao criada automaticamente: {path}", file=sys.stderr)
        return config
    return read_json(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta backlogs dos repositorios configurados")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--out", default="-", help="Arquivo JSON de saida ou '-' para stdout")
    parser.add_argument("--repo", action="append", help="Filtra por nome de repo; pode repetir")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-global", action="store_true",
                        help="Ignora o backlog global e usa o modo legado per-projeto (config de repos)")
    parser.add_argument("--global-backlog", default=str(GLOBAL_BACKLOG),
                        help="Caminho do backlog global unico (default: ~/.backlog/backlog.json)")
    args = parser.parse_args()

    repo_filter = set(args.repo) if args.repo else None
    global_path = Path(args.global_backlog).expanduser()

    if not args.no_global and global_path.exists():
        # Modo GLOBAL (default): fonte da verdade unica ~/.backlog/backlog.json
        results, all_items = collect_global(global_path, repo_filter)
        config_ref = str(global_path)
        repos_total = len(results)
    else:
        # Modo legado per-projeto: coleta o .specify/backlog.json de cada repo da config
        config = load_config(Path(args.config).expanduser())
        repos = [repo for repo in config.get("repos", []) if repo.get("enabled", True)]
        if repo_filter:
            repos = [repo for repo in repos if repo.get("name") in repo_filter]
        results = []
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {pool.submit(collect_repo, repo): repo for repo in repos}
            for future in as_completed(futures):
                results.append(future.result())
        all_items = [item for result in results for item in result.get("items", [])]
        config_ref = str(Path(args.config).expanduser())
        repos_total = len(repos)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": config_ref,
        "repos": sorted(results, key=lambda value: str(value.get("repo"))),
        "items": all_items,
        "summary": {
            "repos_total": repos_total,
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
