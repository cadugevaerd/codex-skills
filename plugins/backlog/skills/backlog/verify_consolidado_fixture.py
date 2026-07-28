#!/usr/bin/env python3
"""Deterministic regression check for the Backlog v2 consolidated fixture."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
source = json.loads((ROOT / "backlog.example.json").read_text(encoding="utf-8"))
rendered = (ROOT / "consolidado_backlog.example.md").read_text(encoding="utf-8")


def section_for_heading(text: str, heading: str, max_level: int) -> str:
    """Return one Markdown section, stopping at the next equal/higher heading."""
    match = re.search(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing heading: {heading}"
    tail = text[match.end() :]
    boundary = re.search(rf"^#{{1,{max_level}}}\s", tail, re.MULTILINE)
    return tail[: boundary.start()] if boundary else tail


assert source["contract_version"] == "2"
backlogs = source["backlogs"]
assert isinstance(backlogs, list) and backlogs

items = [item for backlog in backlogs for item in backlog.get("items", [])]
eligible = [item for item in items if not item.get("archived", False)]
expected_ids = [item["id"] for item in eligible]
rendered_ids = re.findall(r"^### ([A-Z][A-Z0-9_-]*-\d+) — ", rendered, re.MULTILINE)
assert rendered_ids == expected_ids, (rendered_ids, expected_ids)

for backlog in backlogs:
    heading = f"## {backlog['code']} — {backlog['name']}"
    backlog_block = section_for_heading(rendered, heading, 2)
    metadata = backlog_block.split("\n### ", 1)[0]
    assert f"- Profile: `{backlog['profile']}`" in metadata
    if backlog.get("bound_path"):
        assert f"- Bound path: `{backlog['bound_path']}`" in metadata

for item in eligible:
    heading = f"### {item['id']} — {item['title']}"
    item_block = section_for_heading(rendered, heading, 3)
    assert f"- Category: `{item['category']}`" in item_block
    assert f"- Status: `{item['status']}`" in item_block
    assert f"- Criticality: `{item['criticality']}`" in item_block
    assert f"- Position: `{item['position']}`" in item_block

print(f"OK consolidated v2 fixture: {len(backlogs)} backlog(s), {len(eligible)} item(s)")
