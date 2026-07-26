#!/usr/bin/env python3
"""Fail-closed stdlib audit for grill-with-docs managed decision artifacts."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ADR_ID = re.compile(r"ADR-\d{4}\Z")
BL_ID = re.compile(r"BL-\d{4}\Z")
DQ_ID = re.compile(r"DQ-\d{4}\Z")
PHASE_ID = re.compile(r"FASE-\d{3}\Z")
PHASE_HEADER = re.compile(r"^## (FASE-\d{3}) — (.+)$")
DQ_HEADER = re.compile(r"^## (DQ-\d{4}) — (.+)$")
ROUND_ID = re.compile(r"R-(\d{4})\Z")
REF = re.compile(r"\b(?:ADR|BL)-\d{4}\b")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
TOP = re.compile(r"^([A-Za-z][\w-]*):\s*(.*?)\s*$")
FIELD = re.compile(r"^-\s*([\w/-]+):\s*(.*?)\s*$", re.M)
SOURCE_TYPES = {"official-doc", "code", "test", "existing-adr", "user-decision", "inference"}
ADR_STATUSES = {"proposed", "conditional", "accepted", "superseded", "deprecated"}
EVIDENCE = {"verified", "partial", "unverified"}
PHASE_STATES = {"planned", "ready-for-specify", "blocked", "complete", "superseded"}
DQ_STATES = {"open", "resolved", "deferred", "split", "blocked", "out-of-scope"}
SESSION_STATUSES = {"in-progress", "ready", "complete", "blocked", "safety-stop", "paused-user", "superseded"}


def csv(value: str) -> list[str]:
    if value.strip().lower() == "none":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


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
        return None, [f"{path}: {error}" for error in errors], []
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
    if fields.get("status") not in ADR_STATUSES:
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
    return {"id": aid, "fields": fields, "relationships": relationships, "path": path}, [f"{prefix}: {error}" if not error.startswith(prefix) else error for error in errors], refs


def parse_context_terms(root: Path, errors: list[str]) -> set[str]:
    path = root / "CONTEXT.md"
    if not path.exists():
        errors.append("CONTEXT.md ausente")
        return set()
    terms: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] and cells[0] != "Termo canônico" and "<!--" not in cells[0]:
            terms.add(cells[0])
    if not terms:
        errors.append("CONTEXT.md: glossário sem termos canônicos")
    return terms


def phase_handoff_errors(path: Path, phase_id: str, phase_state: str, context_terms: set[str]) -> list[str]:
    errors: list[str] = []
    if not path.exists() or not path.is_file():
        return [f"{phase_id}: specify-handoff inexistente: {path}"]
    text = path.read_text(encoding="utf-8")
    if not re.search(rf"^# {re.escape(phase_id)}(?:\s|—|-)", text, re.M):
        errors.append(f"{phase_id}: handoff não identifica a fase")
    fields = {match.group(1): match.group(2).strip() for match in FIELD.finditer(text)}
    if fields.get("roadmap") != f"ROADMAP.md#{phase_id}":
        errors.append(f"{phase_id}: handoff roadmap inválido")
    if not fields.get("state"):
        errors.append(f"{phase_id}: handoff sem state")
    elif phase_state == "ready-for-specify" and fields["state"] != "ready-for-specify":
        errors.append(f"{phase_id}: handoff precisa estar ready-for-specify")
    if not fields.get("context-refs"):
        errors.append(f"{phase_id}: handoff sem context-refs")
    for term in csv(fields.get("context-refs", "none")):
        if term not in context_terms:
            errors.append(f"{phase_id}: handoff referencia termo inexistente: {term}")
    for heading in ("Problema e valor", "Atores e cenários", "Escopo", "Restrições verificadas"):
        if f"## {heading}" not in text:
            errors.append(f"{phase_id}: handoff sem seção {heading}")
    return errors


def audit_roadmap(root: Path, adr_ids: set[str], backlog_text: str) -> tuple[list[str], set[str]]:
    path = root / "ROADMAP.md"
    if not path.exists():
        return [], set()
    errors: list[str] = []
    context_terms = parse_context_terms(root, errors)
    blocks = re.split(r"(?=^## )", path.read_text(encoding="utf-8"), flags=re.M)
    phases: dict[str, set[str]] = {}
    handoffs: set[str] = set()
    for block in blocks:
        if not block.startswith("## "):
            continue
        header = block.splitlines()[0]
        match = PHASE_HEADER.fullmatch(header)
        if not match:
            errors.append(f"ROADMAP: heading de fase inválido: {header}")
            continue
        phase_id = match.group(1)
        if phase_id in phases:
            errors.append(f"ROADMAP: fase duplicada {phase_id}")
            continue
        fields = {item.group(1): item.group(2).strip() for item in FIELD.finditer(block)}
        required = ("state", "objetivo", "scope-in", "scope-out", "context-refs", "ADRs", "BLs", "depends-on", "entrada", "saída", "specify-handoff")
        for key in required:
            if not fields.get(key):
                errors.append(f"ROADMAP {phase_id}: {key} ausente")
        if fields.get("state") not in PHASE_STATES:
            errors.append(f"ROADMAP {phase_id}: state inválido")
        refs = csv(fields.get("context-refs", "none"))
        if not refs:
            errors.append(f"ROADMAP {phase_id}: context-refs vazio")
        for term in refs:
            if term not in context_terms:
                errors.append(f"ROADMAP {phase_id}: termo inexistente em CONTEXT: {term}")
        adrs = csv(fields.get("ADRs", "none"))
        if not adrs and not fields.get("ADRs-justificativa"):
            errors.append(f"ROADMAP {phase_id}: ADRs none requer ADRs-justificativa")
        for adr in adrs:
            if not ADR_ID.fullmatch(adr) or adr not in adr_ids:
                errors.append(f"ROADMAP {phase_id}: ADR órfão {adr}")
        for bl in csv(fields.get("BLs", "none")):
            if not BL_ID.fullmatch(bl) or bl not in backlog_text:
                errors.append(f"ROADMAP {phase_id}: BL órfão {bl}")
        handoff = fields.get("specify-handoff", "")
        if handoff:
            if handoff in handoffs:
                errors.append(f"ROADMAP {phase_id}: specify-handoff duplicado")
            handoffs.add(handoff)
            errors.extend(phase_handoff_errors(root / handoff, phase_id, fields.get("state", ""), context_terms))
        deps = set(csv(fields.get("depends-on", "none")))
        phases[phase_id] = deps
    if not phases:
        errors.append("ROADMAP: nenhuma fase FASE-NNN")
    for phase_id, deps in phases.items():
        for dep in deps:
            if not PHASE_ID.fullmatch(dep) or dep not in phases:
                errors.append(f"ROADMAP {phase_id}: dependência inexistente {dep}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(phase_id: str) -> None:
        if phase_id in visiting:
            errors.append(f"ROADMAP: ciclo detectado em {phase_id}")
            return
        if phase_id in visited:
            return
        visiting.add(phase_id)
        for dep in phases.get(phase_id, set()):
            if dep in phases:
                visit(dep)
        visiting.remove(phase_id)
        visited.add(phase_id)

    for phase_id in phases:
        visit(phase_id)
    return errors, set(phases)


def audit_frontier(root: Path, phase_ids: set[str], context_terms: set[str]) -> tuple[list[str], set[str]]:
    path = root / "DECISION-FRONTIER.md"
    if not path.exists():
        return ["DECISION-FRONTIER.md ausente"], set()
    errors: list[str] = []
    dq_ids: set[str] = set()
    fingerprints: set[str] = set()
    blocks = re.split(r"(?=^## )", path.read_text(encoding="utf-8"), flags=re.M)
    for block in blocks:
        if not block.startswith("## "):
            continue
        header = block.splitlines()[0]
        match = DQ_HEADER.fullmatch(header)
        if not match:
            errors.append(f"FRONTIER: heading DQ inválido {header}")
            continue
        heading = match.group(1)
        if heading in dq_ids:
            errors.append(f"FRONTIER: DQ duplicada {heading}")
        dq_ids.add(heading)
        fields = {item.group(1): item.group(2).strip() for item in FIELD.finditer(block)}
        for key in ("phase", "fingerprint", "impact", "state", "context-refs", "artifacts", "depends-on", "final-ref"):
            if not fields.get(key):
                errors.append(f"FRONTIER {heading}: {key} ausente")
        if fields.get("phase") not in phase_ids:
            errors.append(f"FRONTIER {heading}: phase inexistente")
        if fields.get("impact") not in {"high", "medium", "low"}:
            errors.append(f"FRONTIER {heading}: impact inválido")
        if fields.get("state") not in DQ_STATES:
            errors.append(f"FRONTIER {heading}: state inválido")
        fingerprint = fields.get("fingerprint", "")
        if fingerprint in fingerprints:
            errors.append(f"FRONTIER: fingerprint duplicado {fingerprint}")
        fingerprints.add(fingerprint)
        for term in csv(fields.get("context-refs", "none")):
            if term not in context_terms:
                errors.append(f"FRONTIER {heading}: termo inexistente em CONTEXT: {term}")
        if fields.get("state") in {"resolved", "deferred", "blocked", "out-of-scope"} and fields.get("final-ref", "none").lower() == "none":
            errors.append(f"FRONTIER {heading}: state terminal requer final-ref")
    if not dq_ids:
        errors.append("FRONTIER: nenhuma DQ-NNNN")
    return errors, dq_ids


def audit_round_log(root: Path, dq_ids: set[str]) -> list[str]:
    path = root / "ROUND-LOG.jsonl"
    if not path.exists():
        return ["ROUND-LOG.jsonl ausente"]
    errors: list[str] = []
    seen: set[str] = set()
    previous_round = 0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"ROUND-LOG linha {number}: JSON inválido: {exc.msg}")
            continue
        for key in ("round_id", "question_id", "transition", "evidence", "artifacts_changed", "progress_delta", "scope_delta", "next_action"):
            if key not in entry:
                errors.append(f"ROUND-LOG linha {number}: {key} ausente")
        if entry.get("round_id") in seen:
            errors.append(f"ROUND-LOG: round_id duplicado {entry.get('round_id')}")
        seen.add(entry.get("round_id", ""))
        round_match = ROUND_ID.fullmatch(str(entry.get("round_id", "")))
        if not round_match:
            errors.append(f"ROUND-LOG linha {number}: round_id inválido")
        elif int(round_match.group(1)) <= previous_round:
            errors.append(f"ROUND-LOG linha {number}: round_id não monotônico")
        else:
            previous_round = int(round_match.group(1))
        if entry.get("question_id") not in dq_ids:
            errors.append(f"ROUND-LOG linha {number}: question_id inexistente")
        if entry.get("transition") not in {"resolved", "deferred", "split", "blocked", "out-of-scope"}:
            errors.append(f"ROUND-LOG linha {number}: transition inválida")
        if not isinstance(entry.get("progress_delta"), dict):
            errors.append(f"ROUND-LOG linha {number}: progress_delta deve ser objeto")
    return errors


def audit_state(root: Path, phase_ids: set[str]) -> list[str]:
    path = root / "state.json"
    if not path.exists():
        return ["state.json ausente"]
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"state.json inválido: {exc.msg}"]
    errors: list[str] = []
    if state.get("status") not in SESSION_STATUSES:
        errors.append("state.json: status inválido")
    if state.get("active_phase") not in phase_ids:
        errors.append("state.json: active_phase inexistente")
    limits = state.get("limits")
    if not isinstance(limits, dict):
        errors.append("state.json: limits ausente")
    else:
        for key in ("max_questions_per_run", "max_question_repeats", "max_clarifications_per_question", "max_no_progress_rounds", "max_scope_growth_streak"):
            if not isinstance(limits.get(key), int) or limits[key] < 1:
                errors.append(f"state.json: limite inválido {key}")
    if state.get("status") in {"blocked", "safety-stop", "paused-user"} and state.get("audit_verdict") == "GO":
        errors.append("state.json: estado não pronto não pode ter audit_verdict GO")
    return errors


def audit(root: Path) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    records: list[dict] = []
    ids: dict[str, Path] = {}
    backlog = root / "DECISION-BACKLOG.md"
    backlog_text = backlog.read_text(encoding="utf-8") if backlog.exists() else ""
    for bid in sorted(set(re.findall(r"\bBL-\d{4}\b", backlog_text))):
        chunk = backlog_text[backlog_text.find(bid):].split("\n## ", 1)[0]
        for required in ("evidência necessária", "responsável", "gatilho de retomada", "ponto de parada"):
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
        if rel.get("superseded-by") in by_id and by_id[rel["superseded-by"]]["relationships"].get("supersedes") != record["id"]:
            errors.append(f"{record['path'].name}: supersession sem backlink")
        if rel.get("supersedes") in by_id and by_id[rel["supersedes"]]["relationships"].get("superseded-by") != record["id"]:
            errors.append(f"{record['path'].name}: supersedes sem backlink")
    roadmap_errors, phase_ids = audit_roadmap(root, set(by_id), backlog_text)
    errors.extend(roadmap_errors)
    if (root / "ROADMAP.md").exists():
        context_errors: list[str] = []
        context_terms = parse_context_terms(root, context_errors)
        errors.extend(context_errors)
        frontier_errors, dq_ids = audit_frontier(root, phase_ids, context_terms)
        errors.extend(frontier_errors)
        errors.extend(audit_round_log(root, dq_ids))
        errors.extend(audit_state(root, phase_ids))
    return records, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print("BLOCKED: diretório inexistente", file=sys.stderr)
        return 2
    records, errors = audit(args.root)
    print(f"Audited managed ADRs: {len(records)}")
    if errors:
        print("NO-GO")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
