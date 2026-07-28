#!/usr/bin/env python3
"""Deterministic regression check for the Backlog v2 consolidated fixture."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
source = json.loads((ROOT / "backlog.example.json").read_text())
rendered = (ROOT / "consolidado_backlog.example.md").read_text()

assert source["contract_version"] == "2"
backlogs = source["backlogs"]
assert isinstance(backlogs, list) and backlogs

items = [item for backlog in backlogs for item in backlog.get("items", [])]
eligible = [item for item in items if not item.get("archived", False)]
expected_ids = [item["id"] for item in eligible]
rendered_ids = re.findall(r"^### ([A-Z][A-Z0-9_-]*-\d+) — ", rendered, re.MULTILINE)
assert rendered_ids == expected_ids, (rendered_ids, expected_ids)

for backlog in backlogs:
    assert f"## {backlog['code']} — {backlog['name']}" in rendered
    assert f"- Profile: `{backlog['profile']}`" in rendered
    if backlog.get("bound_path"):
        assert f"- Bound path: `{backlog['bound_path']}`" in rendered

for item in eligible:
    assert f"### {item['id']} — {item['title']}" in rendered
    assert f"- Category: `{item['category']}`" in rendered
    assert f"- Status: `{item['status']}`" in rendered
    assert f"- Criticality: `{item['criticality']}`" in rendered
    assert f"- Position: `{item['position']}`" in rendered

print(f"OK consolidated v2 fixture: {len(backlogs)} backlog(s), {len(eligible)} item(s)")
