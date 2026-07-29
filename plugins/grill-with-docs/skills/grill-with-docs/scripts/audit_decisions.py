#!/usr/bin/env python3
"""Deterministic, read-only Spec Kit readiness auditor (stdlib only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PHASE_ID = re.compile(r"^FASE-\d{3}$")
ADR_ID = re.compile(r"^ADR-\d{4}$")
BL_ID = re.compile(r"^BL-\d{4}$")
DQ_ID = re.compile(r"^DQ-\d{4}$")
ROUND_ID = re.compile(r"^R-(\d{4})$")
FIELD = re.compile(r"(?m)^\s*-\s*([\w/-]+):\s*(.*?)\s*$")
TOP_FIELD = re.compile(r"(?m)^([\w-]+):\s*(.*?)\s*$")
TECH_HEADING = re.compile(
    r"^##\s+(Stack|Banco|Framework|Classes|Componentes|Implementação|API interna)\b",
    re.IGNORECASE | re.MULTILINE,
)
TECH_FIELD_NAMES = {
    "stack",
    "banco",
    "framework",
    "classes",
    "componentes",
    "implementação",
    "api-interna",
    "api interna",
}
PHASE_STATES = {"planned", "ready-for-specify", "blocked", "complete", "superseded"}
BL_STATES = {"open", "resolved", "superseded"}
DQ_STATES = {"open", "resolved", "deferred", "split", "blocked", "out-of-scope"}
SESSION_STATES = {"in-progress", "ready", "blocked", "safety-stop", "paused-user", "complete"}


@dataclass(frozen=True)
class Phase:
    phase_id: str
    state: str
    context_refs: tuple[str, ...]
    adrs: tuple[str, ...]
    bls: tuple[str, ...]
    dependencies: tuple[str, ...]
    handoff_raw: str


def csv(value: str | None) -> tuple[str, ...]:
    if not value or value.strip().lower() == "none":
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def fields(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in FIELD.finditer(text)}


def top_fields(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in TOP_FIELD.finditer(text)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def managed_path(
    root: Path,
    raw: str,
    label: str,
    findings: list[str],
    *,
    kind: str = "file",
    direct_parent: str | None = None,
) -> Path | None:
    if not raw:
        findings.append(f"{label}: path ausente")
        return None
    relative = Path(raw)
    if relative.is_absolute():
        findings.append(f"{label}: path absoluto proibido: {raw}")
        return None
    candidate = root / relative
    current = root
    try:
        for component in relative.parts:
            if component in ("", "."):
                continue
            current = current / component
            if current.is_symlink():
                findings.append(f"{label}: symlink proibido: {raw}")
                return None
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, ValueError):
        findings.append(f"{label}: path escapes project: {raw}")
        return None
    if direct_parent and resolved.parent != (root / direct_parent).resolve():
        findings.append(f"{label}: deve estar diretamente em {direct_parent}/")
        return None
    exists = resolved.is_file() if kind == "file" else resolved.is_dir()
    if not exists:
        findings.append(f"required input missing: {raw}")
    return resolved


def split_blocks(text: str, prefix: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        rf"(?ms)^##\s+({re.escape(prefix)}-\d{{3,4}})\b(.*?)(?=^##\s+{re.escape(prefix)}-|\Z)"
    )
    return [(match.group(1), match.group(2)) for match in pattern.finditer(text)]


def state_path_matches(root: Path, raw: object, expected: Path) -> bool:
    if not isinstance(raw, str) or not raw:
        return False
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return candidate.resolve() == expected.resolve()
    except OSError:
        return False


def audit(root_arg: Path) -> tuple[list[str], list[str], str | None, Path | None]:
    root = root_arg.resolve()
    findings: list[str] = []
    blockers: list[str] = []

    constitution = managed_path(root, ".specify/memory/constitution.md", "constitution", findings)
    constitution_template = managed_path(
        root,
        ".specify/templates/constitution-template.md",
        "constitution-template",
        findings,
    )
    workflow = managed_path(root, "WORKFLOW.md", "WORKFLOW", findings)
    context = managed_path(root, "CONTEXT.md", "CONTEXT", findings)
    adr_dir = managed_path(root, "docs/adr", "docs/adr", findings, kind="dir")
    roadmap = managed_path(root, "ROADMAP.md", "ROADMAP", findings)
    backlog = managed_path(root, "DECISION-BACKLOG.md", "DECISION-BACKLOG", findings)
    plan_context = managed_path(root, "PLAN-CONTEXT.md", "PLAN-CONTEXT", findings)
    frontier = managed_path(root, "DECISION-FRONTIER.md", "DECISION-FRONTIER", findings)
    round_log = managed_path(root, "ROUND-LOG.jsonl", "ROUND-LOG", findings)
    state_path = managed_path(root, "state.json", "state", findings)

    if constitution and constitution.is_file():
        text = constitution.read_text(encoding="utf-8")
        values = {**fields(text), **top_fields(text)}
        placeholders = ("{{", "}}", "YYYY-MM-DD", "<owner", "<regra", "<processo", "[PLACEHOLDER]")
        if any(token in text for token in placeholders):
            findings.append("constitution: placeholders presentes")
        if not SEMVER.fullmatch(values.get("version", "")):
            findings.append("constitution: version SemVer inválida")
        for key in ("ratified", "last-amended"):
            if not ISO_DATE.fullmatch(values.get(key, "")):
                findings.append(f"constitution: {key} ISO inválido")
        if not values.get("governance", "").strip():
            findings.append("constitution: governance vazio")
    # Presence and path safety of the local template are mandatory; its placeholders are expected.
    _ = constitution_template

    if workflow and workflow.is_file():
        text = workflow.read_text(encoding="utf-8")
        markers = re.findall(r"grill-with-docs-workflow:(v\d+)", text)
        if markers != ["v1"]:
            findings.append("WORKFLOW: marker/version deve ser exatamente v1")
        essentials = (
            "ROADMAP.md",
            "PLAN-CONTEXT.md",
            "DECISION-BACKLOG.md",
            "DECISION-FRONTIER.md",
            "ROUND-LOG.jsonl",
            "state.json",
            "docs/adr/",
            "handoffs/",
            "agent-assign",
            "PLAN_ONLY_STOP",
        )
        for essential in essentials:
            if essential not in text:
                findings.append(f"WORKFLOW: essencial ausente {essential}")

    context_terms: set[str] = set()
    if context and context.is_file():
        for line in context.read_text(encoding="utf-8").splitlines():
            if line.startswith("|") and "---" not in line:
                first = line.strip("|").split("|")[0].strip()
                if first and first.lower() not in {"termo canônico", "term"}:
                    context_terms.add(first)
        if not context_terms:
            findings.append("CONTEXT.md: glossário vazio")

    legacy_adr = root / "adrs"
    if legacy_adr.is_symlink():
        findings.append("adrs legado: symlink proibido")
    elif legacy_adr.is_dir() and any(legacy_adr.iterdir()):
        findings.append("adrs legado: migrar para docs/adr")

    adr_ids: set[str] = set()
    if adr_dir and adr_dir.is_dir():
        for path in sorted(adr_dir.iterdir()):
            if path.is_symlink():
                findings.append(f"ADR: symlink proibido {path.name}")
                continue
            if not path.is_file() or path.suffix != ".md":
                continue
            if not ADR_ID.fullmatch(path.stem):
                findings.append(f"ADR: nome inválido {path.name}")
                continue
            adr_id = path.stem
            if adr_id in adr_ids:
                findings.append(f"ADR: duplicate {adr_id}")
            adr_ids.add(adr_id)
            text = path.read_text(encoding="utf-8")
            values = {**fields(text), **top_fields(text)}
            status = values.get("status", "")
            evidence = values.get("evidence-status", values.get("evidence", ""))
            sources = values.get("sources", values.get("source", ""))
            if not sources and re.search(r"(?ms)^sources:\s*$\n\s+-\s+type:\s*\S+", text):
                sources = "structured-list"
            if status not in {"proposed", "conditional", "accepted", "superseded", "deprecated"}:
                findings.append(f"{adr_id}: status inválido/ausente")
            if evidence not in {"verified", "partial", "unverified"}:
                findings.append(f"{adr_id}: evidence-status inválido/ausente")
            if not sources:
                findings.append(f"{adr_id}: sources ausente")
            if status == "accepted" and evidence == "unverified":
                findings.append(f"{adr_id}: accepted depende de unverified")
            for reference in re.findall(r"\bADR-\d{4}\b", text):
                if reference != adr_id and reference not in adr_ids:
                    # Forward references are checked again after all ADRs below.
                    pass
        for path in sorted(adr_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for reference in re.findall(r"\bADR-\d{4}\b", text):
                if reference != path.stem and reference not in adr_ids:
                    findings.append(f"{path.stem}: ADR orphan {reference}")

    phases: dict[str, Phase] = {}
    execution_order: tuple[str, ...] = ()
    if roadmap and roadmap.is_file():
        text = roadmap.read_text(encoding="utf-8")
        order_match = re.search(r"(?im)^\s*-?\s*execution-order:\s*(.+)$", text)
        if not order_match:
            findings.append("ROADMAP: execution-order ausente")
        else:
            execution_order = csv(order_match.group(1))
        for phase_id, block in split_blocks(text, "FASE"):
            if phase_id in phases:
                findings.append(f"ROADMAP: fase duplicada {phase_id}")
                continue
            values = fields(block)
            required = (
                "state",
                "objetivo",
                "scope-in",
                "scope-out",
                "context-refs",
                "ADRs",
                "BLs",
                "depends-on",
                "specify-handoff",
            )
            for key in required:
                if key not in values or not values[key]:
                    findings.append(f"ROADMAP {phase_id}: {key} ausente")
            phase = Phase(
                phase_id=phase_id,
                state=values.get("state", ""),
                context_refs=csv(values.get("context-refs")),
                adrs=csv(values.get("ADRs")),
                bls=csv(values.get("BLs")),
                dependencies=csv(values.get("depends-on")),
                handoff_raw=values.get("specify-handoff", ""),
            )
            phases[phase_id] = phase
            if phase.state not in PHASE_STATES:
                findings.append(f"ROADMAP {phase_id}: state inválido")
            for reference in phase.context_refs:
                if reference not in context_terms:
                    findings.append(f"ROADMAP {phase_id}: context inexistente {reference}")
            for adr_id in phase.adrs:
                if not ADR_ID.fullmatch(adr_id) or adr_id not in adr_ids:
                    findings.append(f"ROADMAP {phase_id}: ADR orphan {adr_id}")
        if len(execution_order) != len(set(execution_order)) or set(execution_order) != set(phases):
            findings.append("ROADMAP: execution-order incompleta ou duplicada")
        positions = {phase_id: index for index, phase_id in enumerate(execution_order)}
        for phase in phases.values():
            for dependency in phase.dependencies:
                if dependency not in phases:
                    findings.append(f"ROADMAP: dependência inexistente {phase.phase_id}->{dependency}")
                elif positions.get(dependency, 10**9) >= positions.get(phase.phase_id, -1):
                    findings.append(f"ROADMAP: ordem não topológica {phase.phase_id}->{dependency}")

    backlog_items: dict[str, dict[str, str]] = {}
    if backlog and backlog.is_file():
        text = backlog.read_text(encoding="utf-8")
        for bl_id, block in split_blocks(text, "BL"):
            if bl_id in backlog_items:
                findings.append(f"BACKLOG: duplicate {bl_id}")
                continue
            values = fields(block)
            backlog_items[bl_id] = values
            if values.get("state") not in BL_STATES:
                findings.append(f"{bl_id}: state inválido")
            if values.get("phase") not in phases:
                findings.append(f"{bl_id}: phase inválida")
            if values.get("state") == "open":
                for key in ("owner", "evidence-needed", "next-action"):
                    if not values.get(key):
                        findings.append(f"{bl_id}: open exige {key}")
        linked: set[str] = set()
        for phase in phases.values():
            for bl_id in phase.bls:
                linked.add(bl_id)
                if not BL_ID.fullmatch(bl_id) or bl_id not in backlog_items:
                    findings.append(f"ROADMAP {phase.phase_id}: BL orphan {bl_id}")
                elif backlog_items[bl_id].get("phase") != phase.phase_id:
                    findings.append(f"{bl_id}: phase divergence")
        for bl_id in backlog_items:
            if bl_id not in linked:
                findings.append(f"{bl_id}: BL orphan")

    handoff_paths: dict[str, Path] = {}
    seen_handoffs: set[Path] = set()
    for phase in phases.values():
        path = managed_path(
            root,
            phase.handoff_raw,
            f"{phase.phase_id} handoff",
            findings,
            direct_parent="handoffs",
        )
        if not path or not path.is_file():
            continue
        if path in seen_handoffs:
            findings.append(f"{phase.phase_id}: handoff duplicado")
        seen_handoffs.add(path)
        handoff_paths[phase.phase_id] = path
        text = path.read_text(encoding="utf-8")
        values = fields(text)
        if not re.search(rf"(?m)^#\s+{re.escape(phase.phase_id)}\b", text):
            findings.append(f"{phase.phase_id}: handoff phase heading divergence")
        expected_fields = {
            "phase": phase.phase_id,
            "state": phase.state,
            "roadmap": f"ROADMAP.md#{phase.phase_id}",
        }
        for key, expected in expected_fields.items():
            if values.get(key) != expected:
                findings.append(f"{phase.phase_id}: handoff {key} divergence")
        if set(csv(values.get("context-refs"))) != set(phase.context_refs):
            findings.append(f"{phase.phase_id}: handoff context divergence")
        if set(csv(values.get("ADRs"))) != set(phase.adrs):
            findings.append(f"{phase.phase_id}: handoff ADR divergence")
        if set(csv(values.get("BLs"))) != set(phase.bls):
            findings.append(f"{phase.phase_id}: handoff BL divergence")
        if not re.search(r"(?m)^##\s+WHAT\s*$", text) or not re.search(r"(?m)^##\s+WHY\s*$", text):
            findings.append(f"{phase.phase_id}: handoff WHAT/WHY ausente")
        if re.search(r"(?m)^##\s+HOW\s*$", text):
            findings.append(f"{phase.phase_id}: HOW proibido no handoff")
        if TECH_HEADING.search(text):
            findings.append(f"{phase.phase_id}: heading técnico proibido no handoff")
        if any(key.lower() in TECH_FIELD_NAMES for key in values):
            findings.append(f"{phase.phase_id}: campo técnico proibido no handoff")

    if plan_context and plan_context.is_file():
        text = plan_context.read_text(encoding="utf-8")
        if re.search(r"(?im)^\s*-?\s*selected-handoff\s*:", text):
            findings.append("PLAN-CONTEXT não pode ser selected-handoff")
        plan_blocks = dict(split_blocks(text, "FASE"))
        if set(plan_blocks) != set(phases):
            findings.append("PLAN-CONTEXT: blocos de fase divergentes")
        for phase_id, phase in phases.items():
            block = plan_blocks.get(phase_id)
            if block is None:
                findings.append(f"PLAN-CONTEXT: bloco ausente {phase_id}")
                continue
            values = fields(block)
            if values.get("phase") != phase_id:
                findings.append(f"PLAN-CONTEXT {phase_id}: phase divergence")
            if set(csv(values.get("ADRs"))) != set(phase.adrs):
                findings.append(f"PLAN-CONTEXT {phase_id}: ADR divergence")
            if set(csv(values.get("BLs"))) != set(phase.bls):
                findings.append(f"PLAN-CONTEXT {phase_id}: BL divergence")
            how = re.search(r"(?ms)^###\s+HOW\s*$\n(.*?)(?=^###\s+|\Z)", block)
            if not how or not how.group(1).strip():
                findings.append(f"PLAN-CONTEXT {phase_id}: HOW vazio/ausente")

    dq_ids: set[str] = set()
    dq_states: dict[str, str] = {}
    if frontier and frontier.is_file():
        text = frontier.read_text(encoding="utf-8")
        for dq_id, block in split_blocks(text, "DQ"):
            if dq_id in dq_ids:
                findings.append(f"FRONTIER: duplicate {dq_id}")
            dq_ids.add(dq_id)
            values = fields(block)
            if values.get("phase") not in phases:
                findings.append(f"FRONTIER {dq_id}: phase inválida")
            dq_state = values.get("state", "")
            dq_states[dq_id] = dq_state
            if dq_state not in DQ_STATES:
                findings.append(f"FRONTIER {dq_id}: state inválido")
            final_ref = values.get("final-ref", "")
            if dq_state in {"resolved", "deferred", "blocked", "out-of-scope"} and not final_ref:
                findings.append(f"FRONTIER {dq_id}: final-ref ausente")
        if not dq_ids:
            findings.append("FRONTIER: nenhuma DQ")

    if round_log and round_log.is_file():
        previous = 0
        seen_rounds: set[str] = set()
        for line_number, line in enumerate(round_log.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                findings.append(f"ROUND-LOG linha {line_number}: JSON inválido")
                continue
            round_id = str(record.get("round_id", ""))
            match = ROUND_ID.fullmatch(round_id)
            if not match:
                findings.append(f"ROUND-LOG linha {line_number}: round_id inválido")
            else:
                number = int(match.group(1))
                if number <= previous:
                    findings.append(f"ROUND-LOG linha {line_number}: round_id não monotônico")
                previous = number
            if round_id in seen_rounds:
                findings.append(f"ROUND-LOG: duplicate {round_id}")
            seen_rounds.add(round_id)
            if record.get("question_id") not in dq_ids:
                findings.append(f"ROUND-LOG linha {line_number}: question_id orphan")
            if record.get("transition") not in {"resolved", "deferred", "split", "blocked", "out-of-scope"}:
                findings.append(f"ROUND-LOG linha {line_number}: transition inválida")

    ready = [phase_id for phase_id in execution_order if phases.get(phase_id) and phases[phase_id].state == "ready-for-specify"]
    incomplete = [phase_id for phase_id in execution_order if phases.get(phase_id) and phases[phase_id].state not in {"complete", "superseded"}]
    blocked_phase: str | None = None
    selected_phase: str | None = None
    if len(ready) > 1:
        findings.append("ROADMAP: duas ready")
    elif len(ready) == 1:
        selected_phase = ready[0]
        if not incomplete or selected_phase != incomplete[0]:
            findings.append("ROADMAP: ready não é primeira incompleta")
    elif incomplete and phases[incomplete[0]].state == "blocked":
        blocked_phase = incomplete[0]
    else:
        findings.append("ROADMAP: zero ready não-blocked")

    active_phase = selected_phase or blocked_phase
    if active_phase:
        phase = phases[active_phase]
        for dependency in phase.dependencies:
            if phases.get(dependency) and phases[dependency].state not in {"complete", "superseded"}:
                findings.append(f"ROADMAP {active_phase}: dependência não completa {dependency}")
        open_bls = [bl_id for bl_id in phase.bls if backlog_items.get(bl_id, {}).get("state") == "open"]
        if selected_phase and open_bls:
            findings.append("ready ligada a BL open")
        if blocked_phase:
            if not open_bls:
                findings.append("BLOCKED: BL open válido ausente")
            else:
                blockers.append(f"dependência externa legítima: {', '.join(open_bls)}")

    if selected_phase and any(state in {"open", "blocked"} for state in dq_states.values()):
        findings.append("FRONTIER: DQ material open/blocked impede GO")

    state_data: dict[str, object] = {}
    if state_path and state_path.is_file():
        try:
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("state must be object")
            state_data = loaded
        except (json.JSONDecodeError, ValueError):
            findings.append("state.json malformed")
        required_state = ("version", "status", "active_phase", "audit_verdict", "constitution", "workflow", "limits", "second_pass")
        for key in required_state:
            if key not in state_data:
                findings.append(f"state: {key} ausente")
        if not SEMVER.fullmatch(str(state_data.get("version", ""))):
            findings.append("state: version inválida")
        if state_data.get("status") not in SESSION_STATES:
            findings.append("state: status inválido")
        if active_phase and state_data.get("active_phase") != active_phase:
            findings.append("state: active_phase divergence")
        if blocked_phase and state_data.get("audit_verdict") == "GO":
            findings.append("state: blocked não pode ter audit_verdict GO")
        for key, expected in (("constitution", constitution), ("workflow", workflow)):
            value = state_data.get(key)
            if not isinstance(value, dict):
                findings.append(f"state: {key} deve ser objeto")
                continue
            if expected and expected.is_file() and not state_path_matches(root, value.get("path"), expected):
                findings.append(f"state: {key} path divergence")
            if expected and expected.is_file() and value.get("sha256") != sha256(expected):
                findings.append(f"state: {key} hash divergence")
            if key == "workflow" and value.get("version") != "v1":
                findings.append("state: workflow version divergence")
        limits = state_data.get("limits")
        if not isinstance(limits, dict) or not limits:
            findings.append("state: limits ausente/inválido")
        elif any(not isinstance(value, int) or value < 1 for value in limits.values()):
            findings.append("state: limits deve conter inteiros positivos")
        second_pass = state_data.get("second_pass")
        if not isinstance(second_pass, dict) or not isinstance(second_pass.get("new_material_dqs"), int):
            findings.append("state: second_pass inválido")
        elif selected_phase and second_pass["new_material_dqs"] != 0:
            findings.append("state: segunda passada criou DQ material")

    selected_handoff = handoff_paths.get(selected_phase) if selected_phase else None
    if selected_phase and selected_handoff is None:
        findings.append("selected handoff ausente")

    unique_findings = sorted(set(findings))
    if unique_findings:
        blockers.clear()
    return unique_findings, sorted(set(blockers)), selected_phase, selected_handoff


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print("BLOCKED")
        print("- diretório inexistente")
        return 2
    root = args.root.resolve()
    try:
        findings, blockers, selected_phase, selected_handoff = audit(root)
    except UnicodeError:
        print("NO-GO")
        print("- invalid UTF-8 input")
        return 1
    except OSError as error:
        print("NO-GO")
        print(f"- filesystem input error: {type(error).__name__}")
        return 1
    if findings:
        print("NO-GO")
        print("\n".join(f"- {finding}" for finding in findings))
        return 1
    if blockers:
        print("BLOCKED")
        print("\n".join(f"- {blocker}" for blocker in blockers))
        return 2
    print("GO")
    print(f"selected-phase: {selected_phase}")
    relative_handoff = selected_handoff.relative_to(root).as_posix() if selected_handoff else ""
    print(f"selected-handoff: {relative_handoff}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
