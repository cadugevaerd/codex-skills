#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import relatorio_config

CONFIG_PATH = Path.home() / ".claude" / "relatorio-gerencial.json"
DEFAULT_TIMEOUT = 30.0
TERMINAL_STATES = {"done", "cancelled", "merged"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _items_from_export(data: Any) -> list[dict[str, Any]]:
    """Flatten only the v2 consolidated shapes; reject unknown/malformed data."""
    if isinstance(data, list):
        if not all(isinstance(item, dict) for item in data):
            raise ValueError("data lista contem item invalido")
        return list(data)
    if not isinstance(data, dict):
        raise ValueError("data deve ser lista ou objeto consolidado")
    if "items" in data:
        items = data["items"]
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise ValueError("data.items invalido")
        return list(items)
    if "backlogs" in data:
        backlogs = data["backlogs"]
        if not isinstance(backlogs, list):
            raise ValueError("data.backlogs invalido")
        flattened: list[dict[str, Any]] = []
        for backlog in backlogs:
            if not isinstance(backlog, dict) or not isinstance(backlog.get("items"), list):
                raise ValueError("backlog consolidado invalido")
            code = backlog.get("code")
            bound_path = backlog.get("bound_path")
            for item in backlog["items"]:
                if not isinstance(item, dict):
                    raise ValueError("backlog.items contem item invalido")
                enriched = dict(item)
                if code is not None and "backlog_code" not in enriched:
                    enriched["backlog_code"] = code
                if bound_path is not None and "bound_path" not in enriched:
                    enriched["bound_path"] = bound_path
                flattened.append(enriched)
        return flattened
    raise ValueError("data consolidado sem items ou backlogs")


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo": item.get("repo") or item.get("repository"),
        "repo_path": item.get("repo_path") or item.get("bound_path"),
        "backlog_code": item.get("backlog_code"),
        "id": item.get("id") or item.get("code"),
        "title": item.get("title") or item.get("name") or "Item sem titulo",
        "description": item.get("description") or item.get("notes") or item.get("detail") or "",
        "type": item.get("type", "item"),
        "status": item.get("status", "aberto"),
        "priority": item.get("priority") or item.get("criticality") or "media",
        "rank": item.get("rank"),
        "agent": item.get("agent"),
        "source": item.get("source") or "backlogctl",
        "updated": item.get("updated") or item.get("created"),
        "raw": item,
    }


def export_consolidated(db_path: Path, *, backlogctl: str | None = None, timeout: float | None = None) -> dict[str, Any]:
    binary = backlogctl or os.environ.get("BACKLOGCTL_BIN", "backlogctl")
    limit = timeout if timeout is not None else float(os.environ.get("BACKLOGCTL_TIMEOUT", DEFAULT_TIMEOUT))
    command = [binary, "--json", "export", "consolidated", "--db", str(db_path)]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=limit, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        raise RuntimeError(f"falha ao executar backlogctl: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"exit code {completed.returncode}"
        raise RuntimeError(f"backlogctl falhou: {detail}")
    try:
        envelope = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("backlogctl retornou JSON invalido") from exc
    if not isinstance(envelope, dict) or envelope.get("result") != "ok" or "data" not in envelope:
        raise RuntimeError("envelope backlogctl invalido: result/data")
    return envelope


def collect(envelope: dict[str, Any], repo_filter: set[str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = [normalize_item(item) for item in _items_from_export(envelope["data"])]
    items = [item for item in items if str(item.get("status", "")).lower() not in TERMINAL_STATES]
    if repo_filter:
        items = [item for item in items if item.get("repo") in repo_filter]
    by_repo: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_repo.setdefault(str(item.get("repo") or "(sem repositorio)"), []).append(item)
    results = [{"repo": repo, "path": group[0].get("repo_path"), "source": "backlogctl", "ok": True, "items": group, "error": None} for repo, group in sorted(by_repo.items())]
    return results, items


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        config = relatorio_config.default_config()
        relatorio_config.save_config(path, config)
        print(f"Configuracao criada automaticamente: {path}", file=sys.stderr)
        return config
    return read_json(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta backlog exclusivamente via backlogctl")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Metadados/filtros de repositorios")
    parser.add_argument("--db", default=os.environ.get("BACKLOG_DB_PATH"), help="PATH da base usado pelo backlogctl")
    parser.add_argument("--backlogctl", default=None, help="Binario backlogctl (ou BACKLOGCTL_BIN)")
    parser.add_argument("--timeout", type=float, default=None, help="Timeout em segundos (ou BACKLOGCTL_TIMEOUT)")
    parser.add_argument("--out", default="-", help="Arquivo JSON de saida ou '-' para stdout")
    parser.add_argument("--repo", action="append", help="Filtra por nome de repo configurado/item")
    args = parser.parse_args()
    if not args.db:
        parser.error("--db ou BACKLOG_DB_PATH e obrigatorio")
    config = load_config(Path(args.config).expanduser())
    configured = {repo.get("name") for repo in config.get("repos", []) if repo.get("enabled", True)}
    envelope = export_consolidated(Path(args.db).expanduser(), backlogctl=args.backlogctl, timeout=args.timeout)
    results, items = collect(envelope, set(args.repo) if args.repo else None)
    payload = {"generated_at": datetime.now().isoformat(timespec="seconds"), "config": str(Path(args.config).expanduser()), "repos": results, "items": items, "summary": {"repos_total": len(configured) or len(results), "repos_ok": len(results), "items_total": len(items)}, "backlogctl": {"operation": envelope.get("operation"), "contract_version": envelope.get("contract_version"), "warnings": envelope.get("warnings", []), "next_action": envelope.get("next_action")}}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.out == "-":
        print(text, end="")
    else:
        out = Path(args.out).expanduser(); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(text, encoding="utf-8"); print(f"Backlogs coletados: {out}")


if __name__ == "__main__":
    main()
