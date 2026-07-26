#!/usr/bin/env python3
"""Fail-closed stdlib audit for grill-with-docs managed decision artifacts."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ADR_ID = re.compile(r"ADR-\d{4}\Z")
BL_ID = re.compile(r"BL-\d{4}\Z")
REF = re.compile(r"\b(?:ADR|BL)-\d{4}\b")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
TOP = re.compile(r"^([A-Za-z][\w-]*):\s*(.*?)\s*$")
INDENT = re.compile(r"^\s+(.+)$")
SOURCE_TYPES = {"official-doc", "code", "test", "existing-adr", "user-decision", "inference"}
STATUSES = {"proposed", "conditional", "accepted", "superseded", "deprecated"}
EVIDENCE = {"verified", "partial", "unverified"}


def parse_frontmatter(path: Path) -> tuple[dict | None, list[dict], str, list[str]]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, [], text, []
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, [], text, ["frontmatter sem fechamento"]
    errors: list[str] = []
    fields: dict[str, str] = {}
    sources: list[dict[str, str]] = []
    in_sources = False
    current: dict[str, str] | None = None
    for raw in text[4:end].splitlines():
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")):
            if not in_sources:
                errors.append(f"indentação inesperada: {raw}")
                continue
            value = raw.strip()
            if value.startswith("- "):
                value = value[2:].strip()
                current = {}
                sources.append(current)
            if current is None:
                errors.append("item de source sem início")
                continue
            match = TOP.match(value)
            if not match:
                errors.append(f"source inválida: {raw}")
                continue
            key, val = match.groups()
            if key in current:
                errors.append(f"source com campo duplicado: {key}")
            current[key] = val.strip("'\"")
            continue
        match = TOP.match(raw)
        if not match:
            errors.append(f"campo inválido: {raw}")
            continue
        key, value = match.groups()
        if key == "sources":
            if value:
                errors.append("sources deve ser lista indentada")
            in_sources = True
            current = None
        else:
            in_sources = False
            if key in fields:
                errors.append(f"campo duplicado: {key}")
            fields[key] = value.strip("'\"")
    return fields, sources, text[end + 5 :], errors


def section(body: str, heading: str, following: str | None = None) -> str | None:
    marker = f"## {heading}"
    if marker not in body:
        return None
    result = body.split(marker, 1)[1]
    if following and f"## {following}" in result:
        result = result.split(f"## {following}", 1)[0]
    return result


def relationship_values(body: str) -> dict[str, str]:
    value = section(body, "Relações")
    out: dict[str, str] = {}
    if value is None:
        return out
    for line in value.splitlines():
        match = re.match(r"\s*-\s*(amends|supersedes|superseded-by|backlog|exception):\s*(.*?)\s*$", line)
        if match:
            out[match.group(1)] = match.group(2)
    return out


def paths_for_adrs(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in (root / "docs" / "adr", root / "adrs"):
        if directory.is_dir():
            paths.extend(sorted(directory.glob("*.md")))
    return paths


def audit_adr(path: Path, ids: dict[str, Path], backlog_text: str) -> tuple[dict | None, list[str], list[str]]:
    fields, sources, body, errors = parse_frontmatter(path)
    if fields is None:
        return None, [f"{path}: {e}" for e in errors], []
    if fields.get("managed-by") != "grill-with-docs/v1":
        return None, [], []
    prefix = path.name
    for key in ("id", "title", "status", "evidence-status"):
        if not fields.get(key):
            errors.append(f"{prefix}: campo obrigatório ausente: {key}")
    aid = fields.get("id", "")
    if aid and not ADR_ID.fullmatch(aid):
        errors.append(f"{prefix}: id inválido")
    elif aid in ids:
        errors.append(f"{prefix}: ID duplicado: {aid}")
    elif aid:
        ids[aid] = path
    if fields.get("status") not in STATUSES:
        errors.append(f"{prefix}: status inválido")
    if fields.get("evidence-status") not in EVIDENCE:
        errors.append(f"{prefix}: evidence-status inválido")
    if not sources:
        errors.append(f"{prefix}: sources ausente ou vazia")
    for source in sources:
        kind = source.get("type")
        if kind not in SOURCE_TYPES:
            errors.append(f"{prefix}: source type inválido")
            continue
        for key in ("title", "consulted"):
            if not source.get(key):
                errors.append(f"{prefix}: source {kind} sem {key}")
        if source.get("consulted") and not DATE.fullmatch(source["consulted"]):
            errors.append(f"{prefix}: consulted deve ser YYYY-MM-DD")
        if kind == "official-doc":
            for key in ("url", "section"):
                if not source.get(key):
                    errors.append(f"{prefix}: official-doc sem {key}")
    if fields.get("status") == "accepted":
        if fields.get("evidence-status") == "unverified":
            errors.append(f"{prefix}: accepted depende de unverified")
        if not sources:
            errors.append(f"{prefix}: accepted sem fonte")
    for heading in ("Contexto", "Decisão", "Opções e custos", "Consequências", "Relações"):
        if section(body, heading) is None:
            errors.append(f"{prefix}: seção obrigatória ausente: {heading}")
    options = section(body, "Opções e custos", "Consequências")
    option_lines = [line for line in (options or "").splitlines() if line.strip().startswith("-")]
    if len(option_lines) < 2 or any("custo" not in line.lower() for line in option_lines):
        errors.append(f"{prefix}: toda opção deve ter custo")
    relationships = relationship_values(body)
    if fields.get("status") == "superseded" and not relationships.get("superseded-by"):
        errors.append(f"{prefix}: superseded requer superseded-by")
    refs = REF.findall(body)
    return {"id": aid, "fields": fields, "relationships": relationships, "path": path}, [f"{prefix}: {e}" if not e.startswith(prefix) else e for e in errors], refs


def audit_roadmap(root: Path, adr_ids: set[str], backlog_text: str) -> list[str]:
    path = root / "ROADMAP.md"
    if not path.exists():
        return []
    errors: list[str] = []
    blocks = re.split(r"(?=^## )", path.read_text(encoding="utf-8"), flags=re.M)
    stages: dict[str, set[str]] = {}
    for block in blocks:
        if not block.startswith("## "):
            continue
        name = block.splitlines()[0][3:].strip()
        fields = {m.group(1): m.group(2).strip() for m in re.finditer(r"^-\s*([\w/-]+):\s*(.*?)\s*$", block, re.M)}
        for required in ("ADRs/BLs", "depends-on", "entrada", "saída"):
            if not fields.get(required):
                errors.append(f"ROADMAP {name}: {required} ausente")
        for ref in REF.findall(block):
            if ref.startswith("ADR-") and ref not in adr_ids:
                errors.append(f"ROADMAP: referência órfã {ref}")
            if ref.startswith("BL-") and ref not in backlog_text:
                errors.append(f"ROADMAP: BL órfão {ref}")
        deps = set() if fields.get("depends-on", "none").lower() == "none" else {x.strip() for x in fields.get("depends-on", "").split(",") if x.strip()}
        stages[name] = deps
    for name, deps in stages.items():
        for dep in deps:
            if dep not in stages:
                errors.append(f"ROADMAP {name}: dependência inexistente {dep}")
    visiting: set[str] = set(); visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"ROADMAP: ciclo detectado em {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in stages.get(node, set()):
            if dep in stages:
                visit(dep)
        visiting.remove(node); visited.add(node)
    for name in stages:
        visit(name)
    return errors


def audit(root: Path) -> tuple[list[dict], list[str]]:
    errors: list[str] = []; records: list[dict] = []; ids: dict[str, Path] = {}
    backlog = root / "DECISION-BACKLOG.md"
    backlog_text = backlog.read_text(encoding="utf-8") if backlog.exists() else ""
    for bid in sorted(set(re.findall(r"\bBL-\d{4}\b", backlog_text))):
        chunk = backlog_text[backlog_text.find(bid):]
        chunk = chunk.split("\n## ", 1)[0]
        for required in ("evidência necessária", "gatilho de retomada"):
            if required not in chunk.lower():
                errors.append(f"{bid}: {required} ausente")
    all_refs: list[tuple[dict, str]] = []
    for path in paths_for_adrs(root):
        record, found, refs = audit_adr(path, ids, backlog_text)
        errors.extend(found)
        if record:
            records.append(record)
            all_refs.extend((record, ref) for ref in refs)
    for record, ref in all_refs:
        if ref.startswith("ADR-") and ref not in ids:
            errors.append(f"{record['path'].name}: referência órfã {ref}")
        if ref.startswith("BL-") and ref not in backlog_text:
            errors.append(f"{record['path'].name}: BL órfão {ref}")
    by_id = {record["id"]: record for record in records}
    for record in records:
        rel = record["relationships"]
        if rel.get("superseded-by") in by_id:
            target = by_id[rel["superseded-by"]]
            if target["relationships"].get("supersedes") != record["id"]:
                errors.append(f"{record['path'].name}: supersession sem backlink")
        if rel.get("supersedes") in by_id:
            target = by_id[rel["supersedes"]]
            if target["relationships"].get("superseded-by") != record["id"]:
                errors.append(f"{record['path'].name}: supersedes sem backlink")
    errors.extend(audit_roadmap(root, set(by_id), backlog_text))
    return records, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print("BLOCKED: diretório inexistente", file=sys.stderr); return 2
    records, errors = audit(args.root)
    print(f"Audited managed ADRs: {len(records)}")
    if errors:
        print("NO-GO"); print("\n".join(f"- {error}" for error in errors)); return 1
    print("GO"); return 0

if __name__ == "__main__":
    raise SystemExit(main())
