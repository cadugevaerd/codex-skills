#!/usr/bin/env python3
"""Deterministic regression check for the Backlog consolidado fixture."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
source = json.loads((ROOT / "backlog.example.json").read_text())
rendered = (ROOT / "consolidado_backlog.example.md").read_text()

active = [item for item in source["items"] if item["status"] in {"aberto", "em-andamento"}]
expected_counts = Counter(item["priority"] for item in active)
label_by_priority = {
    "critica": "🔴 Crítica",
    "alta": "🟠 Alta",
    "media": "🟡 Média",
    "baixa": "🔵 Baixa",
}

assert "## Resumo de prioridade" in rendered
for priority in ("critica", "alta", "media", "baixa"):
    label = label_by_priority[priority]
    count = expected_counts[priority]
    expected = f"- {label}: {count} atividade" + ("" if count == 1 else "s")
    assert expected in rendered, f"missing summary entry: {expected}"

rendered_ids = re.findall(r"^##### (BL-\d{4}) — ", rendered, re.MULTILINE)
expected_ids = [item["id"] for item in active]
assert Counter(rendered_ids) == Counter(expected_ids), (rendered_ids, expected_ids)
assert "##### BL-0011 — " not in rendered, "merged item leaked into consolidado"

priority_context = None
id_priority = {}
for line in rendered.splitlines():
    if line.startswith("### "):
        for priority, label in label_by_priority.items():
            if line == f"### {label}":
                priority_context = priority
                break
        else:
            priority_context = None
    match = re.match(r"^##### (BL-\d{4}) — ", line)
    if match:
        assert priority_context is not None, f"item {match.group(1)} is outside a priority block"
        id_priority[match.group(1)] = priority_context

for item in active:
    assert id_priority[item["id"]] == item["priority"], item

first_cluster = rendered.index("## Cluster: Continuidade do atendimento clínico")
second_cluster = rendered.index("## Cluster: Confiabilidade das informações registradas")
assert first_cluster < second_cluster, "cluster ordering lost urgency/due ordering"
first_body = rendered[first_cluster:second_cluster]
for priority in ("critica", "alta", "media", "baixa"):
    assert f"### {label_by_priority[priority]}" in first_body, priority
assert "#### masterai-agents-backend" in first_body
assert "#### portal-clinicas" in first_body
second_body = rendered[second_cluster:]
for priority in ("alta", "media", "baixa"):
    assert f"### {label_by_priority[priority]}" not in second_body, priority

print("OK consolidado fixture:", len(active), "eligible items;", dict(expected_counts))
