#!/usr/bin/env python3
"""Read-only, deterministic status inventory for Grill work items."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location("grill_workspace_status", HERE.with_name("grill_workspace.py"))
if spec is None or spec.loader is None:
    raise ImportError("cannot load grill_workspace")
workspace = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = workspace
spec.loader.exec_module(workspace)

SEQUENCE = ["specify", "plan", "checklist", "tasks", "analyze", "agent-assign", "agent-execute", "converge", "verify", "review", "ship"]
STATES = {"pending", "in-progress", "complete", "blocked"}

def git(root: Path, *args: str, raw: bool = False) -> str | bytes:
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=not raw, check=False)
    return p.stdout if raw else p.stdout.strip()

def live(root: Path) -> dict[str, Any]:
    return {"branch": git(root, "branch", "--show-current") or "DETACHED", "head": git(root, "rev-parse", "--verify", "HEAD"), "dirty": bool(git(root, "status", "--porcelain=v1", "--untracked-files=all"))}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def parse_json(bundle: Any, name: str) -> dict[str, Any]:
    raw = bundle.files.get(name)
    if raw is None:
        raise workspace.CliFailure(workspace.EXIT_NO_GO, "NO-GO", "MALFORMED-STRUCTURE", name)
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise workspace.CliFailure(workspace.EXIT_NO_GO, "NO-GO", "INVALID-UTF8", name) from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise workspace.CliFailure(workspace.EXIT_NO_GO, "NO-GO", "MALFORMED-JSON", name) from exc
    if not isinstance(value, dict):
        raise workspace.CliFailure(workspace.EXIT_NO_GO, "NO-GO", "MALFORMED-STRUCTURE", name)
    return value

def phases_and_map(files: dict[str, bytes]) -> tuple[list[str], dict[str, str], list[str], list[str], list[str]]:
    def text(name: str) -> str:
        raw = files.get(name, b"")
        try: return raw.decode("utf-8")
        except UnicodeError as exc: raise workspace.CliFailure(1, "NO-GO", "INVALID-UTF8", name) from exc
    roadmap, delivery = text("ROADMAP.md"), text("DELIVERY-MAP.md")
    phases = re.findall(r"(?m)^##\s+(FASE-\d{3})\b", roadmap)
    execution = re.search(r"(?m)^-\s+execution-order:\s*(.+)$", roadmap)
    ordered = [x for x in re.split(r"[ ,]+", execution.group(1)) if re.fullmatch(r"FASE-\d{3}", x)] if execution else phases
    phase_state = {m.group(1): m.group(2) for m in re.finditer(r"(?ms)^##\s+(FASE-\d{3})\b.*?^-\s+state:\s*(\S+)", roadmap)}
    modules = sorted(set(re.findall(r"(?m)^##\s+(MOD-\d{3})\b", delivery)))
    units = sorted(set(re.findall(r"(?m)^###\s+(DU-\d{3})\b", delivery)))
    types = sorted(set(re.findall(r"(?m)^-\s+development-type:\s*(\S+)\s*$", delivery)))
    return ordered, phase_state, modules, units, types

def item_payload(root: Path, bundle: Any) -> dict[str, Any]:
    immutable = workspace.validate_metadata(bundle.metadata, bundle.work_id)
    state = parse_json(bundle, "state.json")
    dev = state.get("development")
    findings: list[str] = []
    if dev is None:
        tracking, current, completed, blocked, steps = "legacy-untracked", "unknown", [], [], {}
    elif not isinstance(dev, dict) or dev.get("schema") != "grill-development/v1" or dev.get("sequence") != SEQUENCE or not isinstance(dev.get("steps"), dict):
        tracking, current, completed, blocked, steps = "invalid", "unknown", [], [], dev.get("steps", {}) if isinstance(dev, dict) else {}
        findings.append("INVALID-DEVELOPMENT-SCHEMA")
    else:
        tracking, steps = "tracked", dev["steps"]
        current = dev.get("current_step")
        completed = [s for s in SEQUENCE if steps.get(s) == "complete"]
        blocked = [s for s in SEQUENCE if steps.get(s) == "blocked"]
        if any(steps.get(s) not in STATES for s in SEQUENCE) or any(steps.get(s) == "complete" and any(steps.get(p) != "complete" for p in SEQUENCE[:SEQUENCE.index(s)]) for s in SEQUENCE):
            findings.append("INVALID-DEVELOPMENT-SEQUENCE")
    phases, phase_states, modules, units, types = phases_and_map(bundle.files)
    lv = live(root)
    if immutable.get("branch") != lv["branch"] or immutable.get("head") != lv["head"]: findings.append("LIVE-VS-RECORDED")
    # Re-read all governance evidence through the same no-follow reader used by
    # writes.  The bundle walk is not sufficient: a symlink can be introduced
    # between discovery and this projection, and root-level constitution files
    # are outside the item bundle.
    constitution, constitution_text, _ = workspace.constitution_info(root)
    if immutable.get("constitution", {}).get("sha256") != constitution.get("sha256"):
        findings.append("CONSTITUTION-HASH-MISMATCH")
    check_path = bundle.origin and Path(bundle.origin) / "CONSTITUTION-CHECK.md"
    audit_path = bundle.origin and Path(bundle.origin) / "AUDIT.md"
    check = workspace.safe_read(check_path, root=root) if check_path and check_path.exists() else None
    audit = workspace.safe_read(audit_path, root=root) if audit_path and audit_path.exists() else None
    if check is not None:
        try:
            workspace.parse_check(check)
        except workspace.CliFailure as exc:
            raise workspace.CliFailure(workspace.EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", exc.code, exc.message) from exc
    receipt = root / ".grill" / "global" / "receipts" / f"{bundle.work_id}.json"
    receipt_bytes = None
    if receipt.exists() or receipt.is_symlink():
        receipt_bytes = workspace.safe_read(receipt, root=root)
    item_location = {"worktree": str(root), "path": bundle.origin, "branch": lv["branch"], "head": lv["head"], "dirty": lv["dirty"], "current": False}
    active = state.get("active_phase")
    snapshot = {name: {"size": len(data), "mtime_ns": (Path(bundle.origin) / name).stat().st_mtime_ns} for name, data in sorted(bundle.files.items())}
    return {"work_id": bundle.work_id, "type": immutable["type"], "slug": immutable["slug"], "fingerprint": bundle.fingerprint, "locations": [item_location], "snapshot": snapshot, "recorded": {"branch": immutable.get("branch"), "head": immutable.get("head"), "base_ref": immutable.get("base_ref"), "base_commit": immutable.get("base_commit")}, "planning": {"status": state.get("status"), "milestone_status": state.get("milestone_status"), "active_phase": active, "phase_state": phase_states.get(active, state.get("phase_state")), "execution_order": phases, "phases": phase_states, "modules": modules, "delivery_units": units, "development_types": types}, "development": {"tracking": tracking, "current_step": current, "completed": completed, "blocked": blocked, "steps": steps}, "governance": {"constitution": {"state": constitution.get("state"), "path": constitution.get("path"), "hash": constitution.get("sha256")}, "check": {"state": "present" if check is not None else "missing", "hash": digest(check) if check is not None else None}, "audit": {"verdict": state.get("audit_verdict"), "hash": digest(audit) if audit is not None else None}, "reconciled": {"path": str(receipt) if receipt_bytes is not None else None, "hash": digest(receipt_bytes) if receipt_bytes is not None else None}}, "blockers": blocked, "findings": sorted(findings), "next_gate": "BLOCKED" if findings or blocked else (SEQUENCE[len(completed)] if len(completed) < len(SEQUENCE) else "complete")}

def worktree_roots(root: Path, current: bool) -> list[Path]:
    if current: return [root]
    def common_dir(tree: Path) -> Path:
        value = Path(str(git(tree, "rev-parse", "--git-common-dir")))
        return (tree / value).resolve() if not value.is_absolute() else value.resolve()
    common = common_dir(root)
    out = git(root, "worktree", "list", "--porcelain", "-z", raw=True)
    assert isinstance(out, bytes)
    roots: list[Path] = []
    for record in out.split(b"\0"):
        if record.startswith(b"worktree "):
            candidate = Path(record[9:].decode("utf-8"))
            if candidate.is_dir() and not candidate.is_symlink() and common_dir(candidate) == common: roots.append(candidate.resolve())
    return sorted(set(roots))

def build_status(root_arg: str | Path, work_id: str | None = None, current_worktree: bool = False) -> tuple[dict[str, Any], int]:
    root = workspace.project_root(root_arg)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for worktree in worktree_roots(root, current_worktree):
        directory = worktree / ".grill" / "work-items"
        if not directory.exists(): continue
        workspace.reject_symlink_chain(worktree, directory, allow_missing=False)
        for item in sorted(directory.iterdir(), key=lambda p: p.name):
            if item.is_symlink():
                raise workspace.CliFailure(workspace.EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(item))
            if not item.is_dir() or (work_id and item.name != work_id): continue
            bundle = workspace.read_local_bundle(worktree, item)
            value = item_payload(worktree, bundle)
            value["locations"][0]["current"] = worktree == root
            grouped.setdefault(bundle.work_id, []).append(value)
    if work_id and work_id not in grouped: return {"schema":"grill-status/v1","verdict":"NO-GO","code":"WORK-ITEM-MISSING","project_root":str(root),"summary":{"total":0,"in_progress":0,"blocked":0,"completed":0},"work_items":[],"next_action":"iniciar"}, 1
    items=[]; global_findings=[]
    for key, variants in sorted(grouped.items()):
        fps={v["fingerprint"] for v in variants}
        base=variants[0]
        base["locations"]=[loc for v in variants for loc in v["locations"]]
        base["locations"] = sorted(base["locations"], key=lambda x: (x["worktree"], x["path"]))
        if len(fps)>1:
            base["variants"] = sorted((copy.deepcopy(v) for v in variants), key=lambda x: (x["fingerprint"], x["locations"][0]["worktree"]))
            base["findings"]=sorted(set(base["findings"]+["DUPLICATE-WORK-ID"])); base["next_gate"]="BLOCKED"; global_findings.append("DUPLICATE-WORK-ID")
        items.append(base)
    summary={"total":len(items),"in_progress":sum(1 for x in items if x["next_gate"] not in {"BLOCKED","complete"}),"blocked":sum(1 for x in items if x["next_gate"]=="BLOCKED"),"completed":sum(1 for x in items if x["next_gate"]=="complete")}
    item_findings = sorted({f for x in items for f in x["findings"]})
    global_findings.extend(item_findings)
    code=global_findings[0] if global_findings else ("OK" if items else "EMPTY")
    return {"schema":"grill-status/v1","verdict":"BLOCKED" if global_findings else "OK","code":code,"project_root":str(root),"summary":summary,"work_items":items,"next_action":"iniciar" if not items else ("resolver-bloqueios" if summary["blocked"] else "continuar")}, 2 if global_findings else 0

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("root"); parser.add_argument("--work-id"); parser.add_argument("--current-worktree",action="store_true")
    try: payload, code=build_status(*vars(parser.parse_args(argv)).values())
    except workspace.CliFailure as exc: payload, code={"schema":"grill-status/v1","verdict":exc.verdict,"code":exc.code,"error":exc.message}, exc.exit_code
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))); return code
if __name__ == "__main__": raise SystemExit(main())
