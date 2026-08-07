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
    r"^#{2,6}\s+(Stack|Banco|Framework|Classes|Componentes|Implementação|API interna)\b",
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
MODULE_KINDS = {"domain", "platform", "cross-cutting"}
DEVELOPMENT_TYPES = {"frontend", "backend", "mobile", "integration", "data", "ml-ai", "infra-iac", "platform-devops", "security", "observability-sre", "qa", "documentation"}
BL_STATES = {"open", "resolved", "superseded"}
DQ_STATES = {"open", "resolved", "deferred", "split", "blocked", "out-of-scope"}
HOTFIX_REQUIRED = ("scope", "reproduction", "evidence", "correction-test", "rollback", "constitution-evidence")
SESSION_STATES = {"in-progress", "ready", "blocked", "safety-stop", "paused-user", "complete"}
MILESTONE_STATES = {"in-progress", "blocked", "completed"}


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


def validate_decomposition(root: Path, roadmap: Path | None, plan: Path | None, findings: list[str]) -> None:
    """Validate the work-item-local decomposition without writing anything."""
    path_findings: list[str] = []
    metadata = managed_path(root, "WORK-ITEM.json", "WORK-ITEM", path_findings)
    enabled = False
    if metadata and metadata.is_file():
        try:
            value = json.loads(metadata.read_text(encoding="utf-8"))
            capability = value.get("capability", {}) if isinstance(value, dict) else {}
            enabled = isinstance(capability, dict) and capability.get("schema") == "v1"
        except (OSError, UnicodeError, json.JSONDecodeError):
            path_findings.append("decomposition: WORK-ITEM capability inválida")
    path = managed_path(root, "DELIVERY-MAP.md", "DELIVERY-MAP", path_findings)
    findings.extend(item for item in path_findings if not item.startswith("required input missing:") or enabled)
    if path is None or not path.is_file():
        if enabled and path is not None: findings.append("decomposition: DELIVERY-MAP ausente")
        return
    try: text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError): findings.append("DELIVERY-MAP: leitura inválida"); return
    schema = re.findall(r"(?m)^\s*decomposition-schema:\s*(\S+)\s*$", text)
    if schema != ["v1"]:
        if enabled or schema: findings.append("decomposition: schema inválido/ausente")
        return
    modules = re.findall(r"(?ms)^##\s+(MOD-\d{3})\b(.*?)(?=^##\s+MOD-|\Z)", text)
    mids = [x[0] for x in modules]
    if len(mids) != len(set(mids)): findings.append("decomposition: MOD duplicate")
    if not modules:
        findings.append("decomposition: nenhum MOD")
        if not re.search(r"(?mi)^\s*modules:\s*none\s*$", text):
            findings.append("decomposition: modules:none ausente")
        elif not re.search(r"(?mi)^\s*modules-justification:\s*\S", text):
            findings.append("decomposition: modules:none exige justificativa")
    mod_graph: dict[str, list[str]] = {}; dus: dict[str, dict[str,str]] = {}; du_mod: dict[str,str] = {}
    for mid, block in modules:
        mf_block = block.split("### DU-", 1)[0]
        mf = dict(re.findall(r"(?m)^-\s+([\w-]+):\s*(.*?)\s*$", mf_block))
        for key in ("module-kind", "responsibility", "boundary", "depends-on"):
            if not mf.get(key): findings.append(f"{mid}: campo obrigatório ausente {key}")
        if mf.get("module-kind") not in MODULE_KINDS: findings.append(f"{mid}: module-kind inválido")
        mod_graph[mid] = [x for x in csv(mf.get("depends-on")) if x != "none"]
        for duid, dublock in re.findall(r"(?ms)^###\s+(DU-\d{3})\b(.*?)(?=^###\s+DU-|\Z)", block):
            if duid in dus: findings.append(f"{duid}: DU duplicate")
            df = dict(re.findall(r"(?m)^-\s+([\w-]+):\s*(.*?)\s*$", dublock)); dus[duid] = df; du_mod[duid] = mid
            for key in ("development-type", "phase", "scope-in", "scope-out", "depends-on", "acceptance"):
                if not df.get(key): findings.append(f"{duid}: campo obrigatório ausente {key}")
            if df.get("development-type") not in DEVELOPMENT_TYPES: findings.append(f"{duid}: development-type inválido")
            if not PHASE_ID.fullmatch(df.get("phase", "")): findings.append(f"{duid}: fase ausente/inválida")
    def check_graph(graph: dict[str,list[str]], label: str) -> None:
        visiting: set[str] = set(); visited: set[str] = set()
        def visit(node: str) -> None:
            if node in visiting: findings.append(f"decomposition: {label} dependency cycle"); return
            if node in visited: return
            visiting.add(node)
            for dep in graph.get(node, []):
                if dep not in graph: findings.append(f"{node}: dependency inexistente {dep}")
                else: visit(dep)
            visiting.remove(node); visited.add(node)
        for node in sorted(graph): visit(node)
    check_graph(mod_graph, "MOD"); check_graph({d:[x for x in csv(f.get("depends-on")) if x != "none"] for d,f in dus.items()}, "DU")
    phases: dict[str,set[str]] = {}
    if roadmap and roadmap.exists():
        rtext = roadmap.read_text(encoding="utf-8")
        for phase, block in split_blocks(rtext, "FASE"):
            match = re.search(r"(?m)^-\s*delivery-units:\s*(.*)$", block)
            phases[phase] = set(csv(match.group(1) if match else ""))
        expected = {}
        for du, df in dus.items(): expected.setdefault(df.get("phase"), set()).add(du)
        if phases != expected: findings.append("decomposition: ROADMAP delivery-units divergence")
    else: findings.append("decomposition: ROADMAP ausente")
    for du, df in dus.items():
        if df.get("phase") not in phases: findings.append(f"{du}: fase não declarada no ROADMAP")
    for handoff in sorted(root.glob("handoffs/FASE-*-SPECIFY-HANDOFF.md")):
        raw_handoff = handoff.relative_to(root).as_posix()
        safe_handoff = managed_path(root, raw_handoff, "handoff", findings)
        if safe_handoff is None or not safe_handoff.is_file():
            continue
        phase_match = re.search(r"FASE-\d{3}", handoff.name)
        if not phase_match:
            continue
        phase = phase_match.group(0)
        try:
            htext = safe_handoff.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            findings.append(f"{handoff.name}: leitura inválida")
            continue
        ids = set(re.findall(r"\bDU-\d{3}\b", htext)); expected = phases.get(phase, set())
        if ids != expected: findings.append(f"{handoff.name}: handoff decomposition divergence")
        type_match = re.search(r"(?m)^-\s*development-type:\s*(.*)$", htext)
        declared_types = set(csv(type_match.group(1) if type_match else ""))
        expected_types = {dus[du].get("development-type") for du in expected if du in dus}
        if declared_types != expected_types: findings.append(f"{handoff.name}: handoff development-type divergence")
        if re.search(r"(?im)^#{2,6}\s+(stack|banco|framework|classes|componentes|implementação|api interna)", htext): findings.append(f"{handoff.name}: technical HOW prohibited")
    if plan and plan.exists():
        ptext = plan.read_text(encoding="utf-8")
        plan_phases = dict(split_blocks(ptext, "FASE"))
        plan_units_match = re.findall(r"(?m)^-\s*delivery-units:\s*(.*)$", ptext)
        all_plan_ids = set().union(*(set(re.findall(r"\bDU-\d{3}\b", value)) for value in plan_units_match))
        expected_plan_ids = set().union(*phases.values()) if phases else set()
        if all_plan_ids != expected_plan_ids:
            findings.append("PLAN-CONTEXT: decomposition delivery-unit divergence")
        if set(plan_phases) != set(phases): findings.append("PLAN-CONTEXT: decomposition phase divergence")
        for phase, expected in phases.items():
            block = plan_phases.get(phase, "")
            unit_match = re.search(r"(?m)^-\s*delivery-units:\s*(.*)$", block)
            ids = set(re.findall(r"\bDU-\d{3}\b", unit_match.group(1) if unit_match else ""))
            if ids != expected: findings.append(f"PLAN-CONTEXT {phase}: decomposition divergence")
            type_match = re.search(r"(?m)^-\s*development-type:\s*(.*)$", block)
            declared_types = set(csv(type_match.group(1) if type_match else ""))
            expected_types = {dus[du].get("development-type") for du in expected if du in dus}
            if declared_types != expected_types: findings.append(f"PLAN-CONTEXT {phase}: development-type divergence")
            how = re.search(r"(?ims)^###\s+HOW\s*$\n(.*?)(?=^###\s+|\Z)", block)
            if not how or not how.group(1).strip(): findings.append(f"PLAN-CONTEXT {phase}: HOW vazio")


def audit(root_arg: Path, project_root_arg: Path | None = None) -> tuple[list[str], list[str], str | None, Path | None, bool]:
    root = root_arg.resolve()
    project_root = (project_root_arg or root_arg).resolve()
    findings: list[str] = []
    blockers: list[str] = []
    legacy = project_root_arg is None
    constitution_findings: list[str] = []
    constitution = managed_path(project_root, ".specify/memory/constitution.md", "constitution", constitution_findings)
    if legacy:
        findings.extend(constitution_findings)
    else:
        findings.extend(item for item in constitution_findings if item != "required input missing: .specify/memory/constitution.md")
    constitution_template = managed_path(project_root, ".specify/templates/constitution-template.md", "constitution-template", findings if legacy else [])
    workflow = managed_path(project_root, "WORKFLOW.md", "WORKFLOW", findings)
    context = managed_path(root, "CONTEXT.md", "CONTEXT", findings)
    adr_dir = managed_path(root, "docs/adr", "docs/adr", findings, kind="dir")
    roadmap = managed_path(root, "ROADMAP.md", "ROADMAP", findings)
    backlog = managed_path(root, "DECISION-BACKLOG.md", "DECISION-BACKLOG", findings)
    plan_context = managed_path(root, "PLAN-CONTEXT.md", "PLAN-CONTEXT", findings)
    frontier = managed_path(root, "DECISION-FRONTIER.md", "DECISION-FRONTIER", findings)
    round_log = managed_path(root, "ROUND-LOG.jsonl", "ROUND-LOG", findings)
    state_path = managed_path(root, "state.json", "state", findings)
    validate_decomposition(root, roadmap, plan_context, findings)

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
        if markers != ["v2"]:
            findings.append("WORKFLOW: marker/version deve ser exatamente v2")
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
        for path in sorted(adr_dir.iterdir()):
            if path.is_symlink() or not path.is_file() or path.suffix != ".md":
                continue
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
        if re.search(r"(?m)^#{2,6}\s+HOW\s*$", text):
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
    terminal_milestone = bool(execution_order) and not incomplete
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
    elif terminal_milestone:
        pass
    else:
        findings.append("ROADMAP: zero ready não-blocked")

    active_phase = selected_phase or blocked_phase
    if terminal_milestone:
        terminal_open_bls = sorted(
            bl_id
            for phase in phases.values()
            for bl_id in phase.bls
            if backlog_items.get(bl_id, {}).get("state") == "open"
        )
        if terminal_open_bls:
            findings.append(f"milestone terminal ligado a BL open: {', '.join(terminal_open_bls)}")
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
    if terminal_milestone and any(state in {"open", "blocked"} for state in dq_states.values()):
        findings.append("FRONTIER: DQ material open/blocked impede conclusão")

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
        milestone_status = state_data.get("milestone_status")
        if milestone_status is not None and milestone_status not in MILESTONE_STATES:
            findings.append("state: milestone_status inválido")
        if terminal_milestone and milestone_status != "completed":
            findings.append("state: milestone terminal exige milestone_status completed")
        if not terminal_milestone and milestone_status == "completed":
            findings.append("state: milestone_status completed exige todas as fases terminais")
        if terminal_milestone and state_data.get("status") != "complete":
            findings.append("state: milestone terminal exige status complete")
        if terminal_milestone and state_data.get("active_phase") is not None:
            findings.append("state: milestone terminal exige active_phase null")
        if terminal_milestone and state_data.get("audit_verdict") != "GO":
            findings.append("state: milestone terminal exige audit_verdict GO")
        if not terminal_milestone and active_phase and state_data.get("active_phase") != active_phase:
            findings.append("state: active_phase divergence")
        if blocked_phase and state_data.get("audit_verdict") == "GO":
            findings.append("state: blocked não pode ter audit_verdict GO")
        for key, expected in (("constitution", constitution), ("workflow", workflow)):
            value = state_data.get(key)
            if not isinstance(value, dict):
                findings.append(f"state: {key} deve ser objeto")
                continue
            if key == "constitution" and not expected:
                if value.get("state") != "not-present" or value.get("path") is not None or value.get("sha256") is not None:
                    findings.append("state: constitution ausente deve ser not-present")
                continue
            path_root = project_root if key in {"constitution", "workflow"} else root
            if expected and expected.is_file() and not state_path_matches(path_root, value.get("path"), expected):
                findings.append(f"state: {key} path divergence")
            if expected and expected.is_file() and value.get("sha256") != sha256(expected):
                findings.append(f"state: {key} hash divergence")
            if key == "workflow" and value.get("version") != "v2":
                findings.append("state: workflow version divergence")
        limits = state_data.get("limits")
        if not isinstance(limits, dict) or not limits:
            findings.append("state: limits ausente/inválido")
        elif any(type(value) is not int or value < 1 for value in limits.values()):
            findings.append("state: limits deve conter inteiros positivos")
        second_pass = state_data.get("second_pass")
        if not isinstance(second_pass, dict) or type(second_pass.get("new_material_dqs")) is not int:
            findings.append("state: second_pass inválido")
        elif selected_phase and second_pass["new_material_dqs"] != 0:
            findings.append("state: segunda passada criou DQ material")

    selected_handoff = handoff_paths.get(selected_phase) if selected_phase else None
    if selected_phase and selected_handoff is None:
        findings.append("selected handoff ausente")

    unique_findings = sorted(set(findings))
    if unique_findings:
        blockers.clear()
    return unique_findings, sorted(set(blockers)), selected_phase, selected_handoff, terminal_milestone


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    json_mode = args.json or args.project_root is not None
    if not args.root.is_dir() or (args.project_root is not None and not args.project_root.is_dir()):
        if not json_mode:
            print("BLOCKED\n- diretório inexistente")
        else:
            print(json.dumps({"verdict": "BLOCKED", "code": "ROOT-MISSING", "findings": ["diretório inexistente"]}, ensure_ascii=False, sort_keys=True))
        return 2
    root = args.root.resolve()
    try:
        findings, blockers, selected_phase, selected_handoff, terminal_milestone = audit(root, args.project_root)
    except UnicodeError:
        if not json_mode:
            print("NO-GO\n- invalid UTF-8 input")
        else:
            print(json.dumps({"verdict": "NO-GO", "code": "INVALID-UTF8", "findings": ["invalid UTF-8 input"]}, ensure_ascii=False, sort_keys=True))
        return 1
    except OSError as error:
        payload = {"verdict": "NO-GO", "code": "FILESYSTEM", "findings": [f"filesystem input error: {type(error).__name__}"]}
        if json_mode:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print("NO-GO\n- " + payload["findings"][0])
        return 1
    if findings:
        if json_mode:
            print(json.dumps({"verdict": "NO-GO", "code": "ARTIFACT-INVALID", "findings": findings}, ensure_ascii=False, sort_keys=True))
        else:
            print("NO-GO\n" + "\n".join(f"- {finding}" for finding in findings))
        return 1
    if blockers:
        if json_mode:
            print(json.dumps({"verdict": "BLOCKED", "code": "EXTERNAL-BLOCKER", "findings": blockers}, ensure_ascii=False, sort_keys=True))
        else:
            print("BLOCKED\n" + "\n".join(f"- {blocker}" for blocker in blockers))
        return 2
    if terminal_milestone:
        if json_mode:
            print(json.dumps({"verdict": "MILESTONE-COMPLETE", "code": "MILESTONE-COMPLETE", "selected_phase": None, "selected_handoff": ""}, ensure_ascii=False, sort_keys=True))
        else:
            print("MILESTONE-COMPLETE\nselected-phase: none\nselected-handoff:")
        return 0
    relative_handoff = selected_handoff.relative_to(root).as_posix() if selected_handoff else ""
    if json_mode:
        print(json.dumps({"verdict": "GO", "code": "OK", "selected_phase": selected_phase, "selected_handoff": relative_handoff}, ensure_ascii=False, sort_keys=True))
    else:
        print(f"GO\nselected-phase: {selected_phase}\nselected-handoff: {relative_handoff}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
