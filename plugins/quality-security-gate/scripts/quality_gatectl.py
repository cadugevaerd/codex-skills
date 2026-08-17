#!/usr/bin/env python3
"""Deterministic Quality Security Gate V2; all target operations are read-only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

GO, NO_GO, BLOCKED, USAGE = 0, 1, 2, 3
MODULES = [
    ("MOD-001", "Repository governance", "governance"),
    ("MOD-002", "Integration protection", "branch protection"),
    ("MOD-003", "Code quality", "format lint build test"),
    ("MOD-004", "Secrets and credentials", "secret controls"),
    ("MOD-005", "SAST and policies", "SAST"),
    ("MOD-006", "Dependencies and license", "dependency controls"),
    ("MOD-007", "Hardened CI/CD", "hardened CI"),
    ("MOD-008", "Artifacts and releases", "release integrity"),
    ("MOD-009", "IaC and container", "IaC/container"),
    ("MOD-010", "Application/API", "application API"),
    ("MOD-011", "Observability and response", "observability"),
    ("MOD-012", "Audit and continuous improvement", "continuous improvement"),
]
MODULE_IDS = [module_id for module_id, _, _ in MODULES]
GATE_MODULES = {
    "GATE-001": {"MOD-001", "MOD-012"},
    "GATE-002": {"MOD-003"},
    "GATE-003": {"MOD-002", "MOD-004"},
    "GATE-004": {f"MOD-{i:03d}" for i in range(5, 11)},
    "GATE-005": {"MOD-010", "MOD-011", "MOD-012"},
}
MODULE_GATES = {
    module_id: {gate for gate, owners in GATE_MODULES.items() if module_id in owners}
    for module_id in MODULE_IDS
}
INSTRUCTIONS = ("AGENTS.md", "CLAUDE.md", ".agents/AGENTS.md", ".claude/CLAUDE.md")
OUTCOMES = {"PASS", "FAIL", "BLOCKED", "N/A"}
STATES = {
    "AUTOMATED_ENFORCED",
    "AUTOMATED_NOT_ENFORCED",
    "AUTOMATED_UNVERIFIED",
    "MANUAL",
    "ABSENT",
    "UNKNOWN",
}
SOURCE_TYPES = {"file", "config", "command", "ci", "api"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ParseError(ValueError):
    pass


class MachineParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ParseError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def emit(payload: dict[str, Any], code: int) -> int:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return code


def root_of(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute() or "\0" in str(path):
        raise ValueError("root must be absolute and NUL-free")
    probe = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    if probe.returncode != 0 or not probe.stdout.strip():
        raise ValueError("Git root required")
    root = Path(probe.stdout.strip()).resolve()
    if not root.is_dir():
        raise ValueError("resolved Git root is not a directory")
    return root


def snapshot(root: Path) -> dict[str, Any]:
    instructions: list[dict[str, Any]] = []
    for relative in INSTRUCTIONS:
        path = root / relative
        item: dict[str, Any] = {"path": relative}
        try:
            if path.is_symlink() or (path.exists() and not path.is_file()):
                item["status"] = "unreadable"
            elif not path.exists():
                item["status"] = "absent"
            else:
                before = path.stat()
                raw = path.read_bytes()
                decoded = raw.decode("utf-8")
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    item["status"] = "changed_during_read"
                else:
                    lowered = decoded.lower()
                    signals = [
                        signal
                        for signal in ("production", "personal data", "payment", "public api", "iam")
                        if signal in lowered
                    ]
                    item.update(
                        status="present",
                        sha256=digest(raw),
                        size=len(raw),
                        encoding="utf-8",
                        read_at=after.st_mtime_ns,
                        signals=signals,
                    )
        except (OSError, UnicodeError):
            item["status"] = "unreadable"
        instructions.append(item)

    fingerprint = hashlib.sha256()
    for base, directories, files in os.walk(root):
        directories[:] = sorted(
            name
            for name in directories
            if name not in {".git", "__pycache__"} and not (Path(base) / name).is_symlink()
        )
        for filename in sorted(files):
            path = Path(base) / filename
            if path.is_symlink():
                continue
            try:
                fingerprint.update(path.relative_to(root).as_posix().encode("utf-8"))
                fingerprint.update(b"\0")
                fingerprint.update(path.read_bytes())
            except OSError:
                return {"root": str(root), "fingerprint": "AMBIGUOUS", "instructions": instructions}
    return {"root": str(root), "fingerprint": fingerprint.hexdigest(), "instructions": instructions}


def classify_risk(current_snapshot: dict[str, Any]) -> tuple[str, list[str]]:
    root = Path(current_snapshot["root"])
    signals = {
        signal
        for item in current_snapshot["instructions"]
        for signal in item.get("signals", [])
    }
    level = 1
    factors: list[str] = []
    if any((root / path).exists() for path in ("Dockerfile", "main.tf", "terraform.tf", ".github/workflows")):
        level = 2
        factors.append("CI/container/IaC")
    if any((root / path).exists() for path in ("package.json", "requirements.txt", "pyproject.toml", "openapi.yaml")):
        level = max(level, 2)
        factors.append("application/dependency")
    if signals:
        level = 3
        factors.append("sensitive production instruction: " + ", ".join(sorted(signals)))
    return f"P{level}", factors


def investigator_tasks(current_snapshot: dict[str, Any], risk_profile: str) -> list[dict[str, Any]]:
    return [
        {
            "task_id": f"TASK-{module_id}",
            "module_id": module_id,
            "snapshot": current_snapshot,
            "scope": scope,
            "allowed_gates": sorted(MODULE_GATES[module_id]),
            "capabilities": ["read_files", "list_files"],
            "budget": {"timeout_seconds": 120, "max_output_bytes": 65536},
            "untrusted_repository_data": True,
            "strict_json": True,
            "read_only": True,
            "risk_profile": risk_profile,
        }
        for module_id, _, scope in MODULES
    ]


def required_gates(profile: str) -> list[str]:
    maximum = {"P1": 3, "P2": 4, "P3": 5}[profile]
    return [f"GATE-{i:03d}" for i in range(1, maximum + 1)]


def default_correction(module_id: str) -> dict[str, Any]:
    return {
        "target": f"{module_id} evidence",
        "action": "Implement the missing control outside this read-only audit",
        "acceptance": "required gate passes with current enforced evidence",
        "post_fix_validation": {"status": "NOT_RUN", "procedure": [f"Re-run {module_id} investigator"]},
    }


def base_report(root: Path) -> dict[str, Any]:
    current_snapshot = snapshot(root)
    profile, factors = classify_risk(current_snapshot)
    return {
        "schema_version": "2.0",
        "plugin_version": "0.2.0",
        "snapshot": current_snapshot,
        "risk": {"profile": profile, "factors": factors},
        "required_gates": required_gates(profile),
        "investigator_tasks": investigator_tasks(current_snapshot, profile),
        "modules": [
            {
                "id": module_id,
                "name": name,
                "status": "NOT_EVALUATED",
                "outcome": "BLOCKED",
                "automation_state": "UNKNOWN",
                "evidence": [],
                "gates": [],
                "finding": None,
                "correction": default_correction(module_id),
            }
            for module_id, name, _ in MODULES
        ],
        "global_failures": [],
    }


def analyze(root: Path) -> tuple[dict[str, Any], int]:
    report = base_report(root)
    unsafe = any(item["status"] not in {"present", "absent"} for item in report["snapshot"]["instructions"])
    unsafe = unsafe or report["snapshot"]["fingerprint"] == "AMBIGUOUS"
    report["verdict"] = "BLOCKED"
    if unsafe:
        report["global_failures"] = [
            {"id": "GATE-000", "outcome": "BLOCKED", "reason": "invalid or ambiguous snapshot"}
        ]
    return report, BLOCKED


def evidence_valid(items: Any) -> bool:
    if not isinstance(items, list) or not items:
        return False
    required = {"source_type", "source", "locator", "digest", "observed"}
    optional = {"tool", "version", "exit_code"}
    for item in items:
        if not isinstance(item, dict) or not required <= set(item) or not set(item) <= required | optional:
            return False
        if item["source_type"] not in SOURCE_TYPES:
            return False
        if not all(isinstance(item[key], str) and item[key] for key in ("source", "locator", "observed")):
            return False
        if not isinstance(item["digest"], str) or not SHA256_RE.fullmatch(item["digest"]):
            return False
        if "exit_code" in item and not isinstance(item["exit_code"], int):
            return False
    return True


def correction_valid(correction: Any) -> bool:
    if not isinstance(correction, dict) or set(correction) != {"target", "action", "acceptance", "post_fix_validation"}:
        return False
    if not all(isinstance(correction[key], str) and correction[key] for key in ("target", "action", "acceptance")):
        return False
    validation = correction["post_fix_validation"]
    return (
        isinstance(validation, dict)
        and set(validation) == {"status", "procedure"}
        and validation.get("status") == "NOT_RUN"
        and isinstance(validation.get("procedure"), list)
        and bool(validation["procedure"])
        and all(isinstance(step, str) and step for step in validation["procedure"])
    )


def finding_valid(finding: Any) -> bool:
    return (
        isinstance(finding, dict)
        and set(finding) == {"id", "severity", "summary", "cause", "impact"}
        and isinstance(finding.get("id"), str)
        and bool(re.fullmatch(r"MOD-(00[1-9]|01[0-2])-F\d{3}", finding["id"]))
        and finding.get("severity") in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        and all(isinstance(finding.get(key), str) and finding[key] for key in ("summary", "cause", "impact"))
    )


def applicability_valid(applicability: Any) -> bool:
    return (
        isinstance(applicability, dict)
        and set(applicability) == {"status", "rationale", "evidence"}
        and applicability.get("status") == "NOT_APPLICABLE"
        and isinstance(applicability.get("rationale"), str)
        and bool(applicability["rationale"])
        and evidence_valid(applicability.get("evidence"))
    )


def gate_valid(module_id: str, gate: Any) -> bool:
    return (
        isinstance(gate, dict)
        and set(gate) == {"id", "outcome", "automation_state", "evidence"}
        and gate.get("id") in MODULE_GATES[module_id]
        and gate.get("outcome") in OUTCOMES
        and gate.get("automation_state") in STATES
        and evidence_valid(gate.get("evidence"))
    )


def validate_module_result(result: Any, current_snapshot: dict[str, Any]) -> tuple[bool, str | None]:
    if not isinstance(result, dict):
        return False, "result is not an object"
    required = {"module_id", "snapshot", "outcome", "automation_state", "evidence", "gates", "finding", "correction"}
    allowed = required | {"applicability"}
    if not required <= set(result) or not set(result) <= allowed:
        return False, "result keys do not match the schema"
    module_id = result["module_id"]
    if module_id not in MODULE_IDS or result["snapshot"] != current_snapshot:
        return False, "module ID or snapshot mismatch"
    if result["outcome"] not in OUTCOMES or result["automation_state"] not in STATES:
        return False, "invalid outcome or automation state"
    if not evidence_valid(result["evidence"]) or not correction_valid(result["correction"]):
        return False, "invalid evidence or correction contract"
    gates = result["gates"]
    if not isinstance(gates, list) or not gates or not all(gate_valid(module_id, gate) for gate in gates):
        return False, "invalid gate result"
    gate_ids = [gate["id"] for gate in gates]
    if len(gate_ids) != len(set(gate_ids)):
        return False, "duplicate gate result"

    outcome = result["outcome"]
    state = result["automation_state"]
    if state == "UNKNOWN" or outcome == "BLOCKED":
        return True, "blocked"
    if outcome == "PASS":
        if state != "AUTOMATED_ENFORCED":
            return False, "PASS is not enforced"
        if any(gate["outcome"] != "PASS" or gate["automation_state"] != "AUTOMATED_ENFORCED" for gate in gates):
            return False, "PASS contains a non-enforced gate"
        if result["finding"] is not None or result.get("applicability") is not None:
            return False, "PASS cannot contain finding or N/A applicability"
    elif outcome == "FAIL":
        if not finding_valid(result["finding"]) or not any(gate["outcome"] == "FAIL" for gate in gates):
            return False, "FAIL lacks a strict finding or failed gate"
    elif outcome == "N/A":
        if not applicability_valid(result.get("applicability")):
            return False, "N/A lacks verifiable non-applicability"
        if any(gate["outcome"] != "N/A" for gate in gates):
            return False, "N/A contains an applicable gate outcome"
    return True, None


def consolidate(root: Path, data: Any) -> tuple[dict[str, Any], int]:
    if not isinstance(data, dict) or set(data) != {"module_results"}:
        raise ValueError("module result envelope must contain only module_results")
    raw = data["module_results"]
    if not isinstance(raw, list):
        raise ValueError("module_results must be an array")

    report = base_report(root)
    ids = [item.get("module_id") for item in raw if isinstance(item, dict)]
    structural_failures: list[str] = []
    if len(raw) != 12 or sorted(ids) != sorted(MODULE_IDS) or len(set(ids)) != 12:
        structural_failures.append("module-result-set")
    by_id = {item.get("module_id"): item for item in raw if isinstance(item, dict)}
    blocked_modules: list[str] = []
    confirmed_failure = False

    for row in report["modules"]:
        result = by_id.get(row["id"])
        valid, reason = validate_module_result(result, report["snapshot"])
        if not valid:
            structural_failures.append(f"{row['id']}: {reason}")
            continue
        row.update({key: result.get(key) for key in ("outcome", "automation_state", "evidence", "gates", "finding", "correction", "applicability")})
        row["status"] = "EVALUATED"
        if reason == "blocked":
            blocked_modules.append(row["id"])
        elif result["outcome"] == "FAIL":
            confirmed_failure = True

    required_assignment_failures: list[str] = []
    for gate_id in report["required_gates"]:
        for module_id in sorted(GATE_MODULES[gate_id]):
            result = by_id.get(module_id)
            gate = next((item for item in result.get("gates", []) if item.get("id") == gate_id), None) if isinstance(result, dict) else None
            if gate is None:
                required_assignment_failures.append(f"{gate_id}:{module_id}:missing")
            elif gate.get("outcome") == "FAIL" and gate_valid(module_id, gate):
                confirmed_failure = True
            elif gate.get("outcome") != "PASS" or gate.get("automation_state") != "AUTOMATED_ENFORCED" or not evidence_valid(gate.get("evidence")):
                required_assignment_failures.append(f"{gate_id}:{module_id}:not-enforced")

    blocked = structural_failures + blocked_modules + required_assignment_failures
    if blocked:
        report["verdict"] = "BLOCKED"
        report["global_failures"] = [
            {
                "id": "GATE-000",
                "outcome": "BLOCKED",
                "reason": "missing, invalid, stale, unknown, or non-enforced evidence",
                "details": blocked,
            }
        ]
        return report, BLOCKED
    if confirmed_failure:
        report["verdict"] = "NO-GO"
        return report, NO_GO
    report["verdict"] = "GO"
    return report, GO


def summarize_evidence(items: list[dict[str, Any]]) -> str:
    return ";".join(f"{item['source_type']}:{item['locator']}@{item['digest'][:12]}" for item in items)


def markdown_report(report: dict[str, Any]) -> str:
    rows = [
        (
            "GATE-000",
            "Global",
            "",
            "BLOCKED" if report.get("global_failures") else "PASS",
            "",
            "",
            "",
            "",
            "NOT_RUN",
        )
    ]
    for module in report["modules"]:
        correction = module.get("correction", {})
        validation = correction.get("post_fix_validation", {})
        rows.append(
            (
                module["id"],
                module["name"],
                ";".join(gate.get("id", "") for gate in module.get("gates", [])),
                module["outcome"],
                module.get("automation_state", ""),
                summarize_evidence(module.get("evidence", [])),
                correction.get("target", ""),
                correction.get("acceptance", ""),
                validation.get("status", "NOT_RUN"),
            )
        )
    header = "| ID | Module | Gate | Outcome | Automation | Evidence | Implementar/corrigir | Critério de aceite | Validação |"
    separator = "|---|---|---|---|---|---|---|---|---|"
    return header + "\n" + separator + "\n" + "\n".join("| " + " | ".join(row) + " |" for row in rows)


def blocked_envelope(reason: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "plugin_version": "0.2.0",
        "verdict": "BLOCKED",
        "global_failures": [{"id": "GATE-000", "outcome": "BLOCKED", "reason": reason}],
        "modules": [
            {"id": module_id, "name": name, "status": "NOT_EVALUATED", "outcome": "BLOCKED"}
            for module_id, name, _ in MODULES
        ],
    }


def parser() -> MachineParser:
    root = MachineParser()
    commands = root.add_subparsers(dest="cmd", required=True, parser_class=MachineParser)
    for name in ("plan", "analyze", "status"):
        command = commands.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--json", action="store_true")
    for name in ("consolidate", "report"):
        command = commands.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--input", required=True)
        command.add_argument("--json", action="store_true")
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        root = root_of(args.root)
        if args.cmd in {"plan", "analyze", "status"}:
            payload, code = analyze(root)
        else:
            payload, code = consolidate(root, json.loads(Path(args.input).read_text(encoding="utf-8")))
        if args.cmd == "report" and not args.json:
            print(markdown_report(payload))
            return code
        return emit(payload, code)
    except ParseError as exc:
        return emit(blocked_envelope(str(exc)), USAGE)
    except (ValueError, json.JSONDecodeError, OSError, subprocess.SubprocessError) as exc:
        return emit(blocked_envelope(str(exc)), BLOCKED)


if __name__ == "__main__":
    sys.exit(main())
