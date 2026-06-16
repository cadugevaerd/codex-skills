#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

THEMES = [
    {
        "key": "qualidade-confiabilidade",
        "emoji": "🛡️",
        "title": "Aumentar confiabilidade das entregas",
        "keywords": ["bug", "falha", "erro", "retry", "teste", "validar", "confiabilidade", "smoke", "eval"],
    },
    {
        "key": "fluxos-agentes",
        "emoji": "🚀",
        "title": "Evoluir fluxos dos agentes",
        "keywords": ["agente", "langgraph", "node", "workflow", "comercial", "medicina", "qualidade", "assistant"],
    },
    {
        "key": "integracoes",
        "emoji": "🔗",
        "title": "Reduzir riscos de integracao",
        "keywords": ["api", "provider", "openrouter", "streaming", "proxy", "metadata", "langsmith", "integracao"],
    },
    {
        "key": "gestao-produto",
        "emoji": "📌",
        "title": "Organizar prioridades de produto",
        "keywords": ["feature", "roadmap", "promovido", "spec", "documentacao", "gestao", "backlog"],
    },
    {
        "key": "divida-tecnica",
        "emoji": "🧹",
        "title": "Diminuir divida tecnica acumulada",
        "keywords": ["debt", "chore", "refator", "duplic", "cleanup", "consolidar", "baseline", "config"],
    },
]

PRIORITY_WEIGHT = {"critica": 4, "alta": 3, "media": 2, "baixa": 1}


def read_backlogs(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("items", []))


def read_manual_tasks(path: Path | None, inline: list[str] | None) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    if inline:
        for idx, text in enumerate(inline, 1):
            tasks.append({"repo": "trabalho-atual", "title": text.strip(), "priority": "alta", "type": "current", "status": "em-andamento", "manual": True, "id": f"ATUAL-{idx:02d}"})
    if not path:
        return tasks
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return tasks
    if path.suffix.lower() == ".json":
        data = json.loads(content)
        raw_items = data if isinstance(data, list) else data.get("items", [])
        for idx, item in enumerate(raw_items, 1):
            if isinstance(item, str):
                tasks.append({"repo": "trabalho-atual", "title": item, "priority": "alta", "type": "current", "status": "em-andamento", "manual": True, "id": f"ATUAL-{idx:02d}"})
            else:
                item = dict(item)
                item.setdefault("repo", "trabalho-atual")
                item.setdefault("priority", "alta")
                item.setdefault("type", "current")
                item.setdefault("status", "em-andamento")
                item["manual"] = True
                tasks.append(item)
        return tasks
    for idx, line in enumerate(content.splitlines(), 1):
        cleaned = re.sub(r"^[-*]\s*", "", line).strip()
        if cleaned:
            tasks.append({"repo": "trabalho-atual", "title": cleaned, "priority": "alta", "type": "current", "status": "em-andamento", "manual": True, "id": f"ATUAL-{idx:02d}"})
    return tasks


def theme_for(item: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(str(item.get(key, "")) for key in ("title", "description", "type", "agent", "source")).lower()
    best = THEMES[-1]
    best_score = -1
    for theme in THEMES:
        score = sum(1 for keyword in theme["keywords"] if keyword in text)
        if score > best_score:
            best = theme
            best_score = score
    return best


def urgency(items: list[dict[str, Any]]) -> str:
    if any(item.get("manual") for item in items):
        return "alta"
    max_weight = max((PRIORITY_WEIGHT.get(str(item.get("priority", "media")).lower(), 2) for item in items), default=2)
    if max_weight >= 4:
        return "critica"
    if max_weight >= 3:
        return "alta"
    if max_weight == 2:
        return "media"
    return "baixa"


def summarize_group(theme: dict[str, Any], items: list[dict[str, Any]]) -> str:
    manual = sum(1 for item in items if item.get("manual"))
    high = sum(1 for item in items if str(item.get("priority", "")).lower() in {"critica", "alta"})
    if manual:
        return "Concentra o trabalho que esta em andamento agora e conecta com pendencias que podem impactar a entrega."
    if high:
        return "Reune pontos de maior risco para reduzir surpresa, retrabalho e bloqueios nas proximas entregas."
    if theme["key"] == "divida-tecnica":
        return "Agrupa melhorias internas que diminuem custo de manutencao e risco acumulado."
    return "Agrupa pendencias relacionadas para facilitar priorizacao e acompanhamento executivo."


def next_action(group_urgency: str) -> str:
    if group_urgency in {"critica", "alta"}:
        return "Priorizar na proxima janela e remover bloqueios de decisao."
    if group_urgency == "media":
        return "Planejar no proximo ciclo, mantendo visibilidade semanal."
    return "Manter no radar e executar quando houver folga operacional."


def build_groups(items: list[dict[str, Any]], max_groups: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    themes_by_key = {theme["key"]: theme for theme in THEMES}
    for item in items:
        theme = {"key": "gestao-produto", "title": "Foco atual informado", "emoji": "🎯"} if item.get("manual") else theme_for(item)
        buckets[theme["key"]].append(item)
        themes_by_key.setdefault(theme["key"], theme)

    ranked = sorted(
        buckets.items(),
        key=lambda kv: (
            any(item.get("manual") for item in kv[1]),
            max(PRIORITY_WEIGHT.get(str(item.get("priority", "media")).lower(), 2) for item in kv[1]),
            len(kv[1]),
        ),
        reverse=True,
    )
    groups = []
    for key, group_items in ranked[:max_groups]:
        theme = themes_by_key[key]
        repos = sorted({str(item.get("repo")) for item in group_items if item.get("repo")})
        group_urgency = urgency(group_items)
        groups.append(
            {
                "title": theme["title"],
                "emoji": theme["emoji"],
                "summary": summarize_group(theme, group_items),
                "repos": repos[:4],
                "urgency": group_urgency,
                "next_action": next_action(group_urgency),
                "microtasks_count": len(group_items),
                "examples": [str(item.get("title", ""))[:120] for item in group_items[:3]],
            }
        )
    return groups


def main() -> None:
    parser = argparse.ArgumentParser(description="Agrupa tasks atuais e backlog em iniciativas gerenciais")
    parser.add_argument("--backlogs", required=True)
    parser.add_argument("--manual-tasks", help="Arquivo txt/json com tasks atuais informadas manualmente")
    parser.add_argument("--task", action="append", help="Task atual inline; pode repetir")
    parser.add_argument("--out", default="-")
    parser.add_argument("--max-groups", type=int, default=5)
    args = parser.parse_args()

    backlog_items = read_backlogs(Path(args.backlogs).expanduser())
    manual_items = read_manual_tasks(Path(args.manual_tasks).expanduser() if args.manual_tasks else None, args.task)
    items = manual_items + backlog_items
    groups = build_groups(items, max(1, args.max_groups))
    payload = {
        "date": date.today().isoformat(),
        "title": "Relatorio gerencial de andamento",
        "audience": "gerente",
        "language": "pt-BR",
        "current_tasks": [item.get("title") for item in manual_items[:6]],
        "groups": groups,
        "stats": {
            "manual_tasks": len(manual_items),
            "backlog_items": len(backlog_items),
            "grouped_initiatives": len(groups),
            "repos": sorted({str(item.get("repo")) for item in backlog_items if item.get("repo")}),
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.out == "-":
        print(text, end="")
    else:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Dados agrupados: {out}")


if __name__ == "__main__":
    main()
