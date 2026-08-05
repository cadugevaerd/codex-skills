#!/usr/bin/env python3
"""Regression matrix for the deterministic Spec Kit readiness auditor."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills/grill-with-docs"
AUDITOR = SKILL / "scripts/audit_decisions.py"
WORKFLOW_TEMPLATE = SKILL / "assets/WORKFLOW.template.md"
FIXTURES = PLUGIN / "tests/fixtures"


def symlink_supported() -> bool:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        target = root / "target"
        target.mkdir()
        try:
            (root / "link").symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
        return True


SYMLINK_SUPPORTED = symlink_supported()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_audit(root: Path, *, relative: bool = False) -> subprocess.CompletedProcess[str]:
    argument = "." if relative else str(root)
    return subprocess.run(
        [sys.executable, str(AUDITOR), argument],
        cwd=root,
        text=True,
        capture_output=True,
    )


def write_project(root: Path, *, blocked: bool = False) -> None:
    for directory in (
        root / ".specify/memory",
        root / ".specify/templates",
        root / "docs/adr",
        root / "handoffs",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    (root / ".specify/templates/constitution-template.md").write_text(
        "version: {{VERSION}}\nratified: YYYY-MM-DD\nlast-amended: YYYY-MM-DD\ngovernance: {{GOVERNANCE}}\n",
        encoding="utf-8",
    )
    constitution = root / ".specify/memory/constitution.md"
    constitution.write_text(
        "version: 1.0.0\nratified: 2026-01-01\nlast-amended: 2026-01-01\ngovernance: Architecture Council\n",
        encoding="utf-8",
    )
    workflow = root / "WORKFLOW.md"
    workflow.write_text(WORKFLOW_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    (root / "CONTEXT.md").write_text(
        "# Context\n\n| Termo canônico | Definição |\n|---|---|\n| API | Contrato externo |\n",
        encoding="utf-8",
    )
    (root / "docs/adr/ADR-0001.md").write_text(
        "id: ADR-0001\nstatus: accepted\nevidence-status: verified\nsources: user-decision\n",
        encoding="utf-8",
    )

    phase_one_state = "blocked" if blocked else "ready-for-specify"
    phase_one_bls = "BL-0001" if blocked else "none"
    phase_two_bls = "none" if blocked else "BL-0001"
    (root / "ROADMAP.md").write_text(
        f"""# ROADMAP
- execution-order: FASE-001, FASE-002

## FASE-001 — Foundation
- state: {phase_one_state}
- objetivo: Establish the external contract
- scope-in: Contract definition
- scope-out: Implementation
- context-refs: API
- ADRs: ADR-0001
- BLs: {phase_one_bls}
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md

## FASE-002 — Delivery
- state: planned
- objetivo: Deliver the contract
- scope-in: Delivery
- scope-out: Future work
- context-refs: API
- ADRs: none
- BLs: {phase_two_bls}
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
""",
        encoding="utf-8",
    )

    if blocked:
        backlog_text = """# Decision Backlog

## BL-0001 — External approval
- state: open
- phase: FASE-001
- owner: Platform owner
- evidence-needed: Approval record
- next-action: Obtain approval
"""
    else:
        backlog_text = """# Decision Backlog

## BL-0001 — Follow-up
- state: resolved
- phase: FASE-002
"""
    (root / "DECISION-BACKLOG.md").write_text(backlog_text, encoding="utf-8")

    def handoff(phase_id: str, state: str, adrs: str, bls: str) -> str:
        return f"""# {phase_id} — Specify handoff
- phase: {phase_id}
- state: {state}
- roadmap: ROADMAP.md#{phase_id}
- context-refs: API
- ADRs: {adrs}
- BLs: {bls}

## WHAT
Describe the user-visible outcome and acceptance boundary.

## WHY
Explain the value and actors.
"""

    (root / "handoffs/FASE-001-SPECIFY-HANDOFF.md").write_text(
        handoff("FASE-001", phase_one_state, "ADR-0001", phase_one_bls),
        encoding="utf-8",
    )
    (root / "handoffs/FASE-002-SPECIFY-HANDOFF.md").write_text(
        handoff("FASE-002", "planned", "none", phase_two_bls),
        encoding="utf-8",
    )
    (root / "PLAN-CONTEXT.md").write_text(
        f"""# Plan Context

## FASE-001 — Foundation
- phase: FASE-001
- ADRs: ADR-0001
- BLs: {phase_one_bls}

### HOW
Use the approved architecture boundary during planning.

## FASE-002 — Delivery
- phase: FASE-002
- ADRs: none
- BLs: {phase_two_bls}

### HOW
Choose implementation details during the external plan step.
""",
        encoding="utf-8",
    )

    dq_state = "blocked" if blocked else "resolved"
    final_ref = "BL-0001" if blocked else "ADR-0001"
    (root / "DECISION-FRONTIER.md").write_text(
        f"""# Decision Frontier

## DQ-0001 — Readiness
- phase: FASE-001
- state: {dq_state}
- final-ref: {final_ref}
""",
        encoding="utf-8",
    )
    (root / "ROUND-LOG.jsonl").write_text(
        json.dumps(
            {
                "round_id": "R-0001",
                "question_id": "DQ-0001",
                "transition": dq_state,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    state = {
        "version": "1.0.0",
        "status": "blocked" if blocked else "ready",
        "milestone_status": "blocked" if blocked else "in-progress",
        "active_phase": "FASE-001",
        "audit_verdict": "BLOCKED" if blocked else "pending",
        "constitution": {
            "path": ".specify/memory/constitution.md",
            "sha256": sha256(constitution),
        },
        "workflow": {
            "path": "WORKFLOW.md",
            "sha256": sha256(workflow),
            "version": "v2",
        },
        "limits": {
            "max_questions_per_run": 25,
            "max_question_repeats": 2,
            "max_no_progress_rounds": 2,
        },
        "second_pass": {"new_material_dqs": 0},
    }
    (root / "state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mark_milestone_terminal(root: Path, final_phase_state: str) -> None:
    roadmap = root / "ROADMAP.md"
    roadmap.write_text(
        roadmap.read_text(encoding="utf-8")
        .replace("- state: ready-for-specify", "- state: complete", 1)
        .replace("- state: planned", f"- state: {final_phase_state}", 1),
        encoding="utf-8",
    )
    first = root / "handoffs/FASE-001-SPECIFY-HANDOFF.md"
    first.write_text(first.read_text(encoding="utf-8").replace("- state: ready-for-specify", "- state: complete", 1), encoding="utf-8")
    second = root / "handoffs/FASE-002-SPECIFY-HANDOFF.md"
    second.write_text(second.read_text(encoding="utf-8").replace("- state: planned", f"- state: {final_phase_state}", 1), encoding="utf-8")
    state_path = root / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.update(status="complete", milestone_status="completed", active_phase=None, audit_verdict="GO")
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class AuditorContract(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="grill-auditor-")
        self.root = Path(self.temporary.name)
        write_project(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def assert_no_go(self, expected: str) -> None:
        result = run_audit(self.root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("NO-GO", result.stdout)
        self.assertIn(expected, result.stdout)

    def test_go_is_deterministic_read_only_and_selects_handoff(self) -> None:
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        first = run_audit(self.root)
        second = run_audit(self.root)
        after = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, after)
        self.assertIn("selected-phase: FASE-001", first.stdout)
        self.assertIn("selected-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md", first.stdout)

    def test_completed_milestone_has_explicit_terminal_verdict(self) -> None:
        mark_milestone_terminal(self.root, "complete")
        result = subprocess.run(
            [sys.executable, str(AUDITOR), str(self.root), "--json"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "code": "MILESTONE-COMPLETE",
                "selected_handoff": "",
                "selected_phase": None,
                "verdict": "MILESTONE-COMPLETE",
            },
        )

    def test_superseded_final_phase_is_legitimate_terminal_state(self) -> None:
        mark_milestone_terminal(self.root, "superseded")
        result = subprocess.run(
            [sys.executable, str(AUDITOR), str(self.root), "--json"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual((payload["verdict"], payload["code"]), ("MILESTONE-COMPLETE", "MILESTONE-COMPLETE"))

    def test_terminal_milestone_requires_terminal_session_state(self) -> None:
        mark_milestone_terminal(self.root, "complete")
        state_path = self.root / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.update(status="ready", active_phase="FASE-002")
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.assert_no_go("milestone terminal exige status complete")

    def test_terminal_milestone_requires_explicit_completed_milestone_state(self) -> None:
        mark_milestone_terminal(self.root, "complete")
        state_path = self.root / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        del state["milestone_status"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.assert_no_go("milestone terminal exige milestone_status completed")

    def test_terminal_milestone_rejects_open_bl_and_dq(self) -> None:
        for kind in ("BL", "DQ"):
            with self.subTest(kind=kind):
                write_project(self.root)
                mark_milestone_terminal(self.root, "superseded")
                if kind == "BL":
                    path = self.root / "DECISION-BACKLOG.md"
                    path.write_text(
                        path.read_text(encoding="utf-8").replace("- state: resolved", "- state: open")
                        + "\n- owner: owner\n- evidence-needed: evidence\n- next-action: action\n",
                        encoding="utf-8",
                    )
                    expected = "milestone terminal ligado a BL open"
                else:
                    path = self.root / "DECISION-FRONTIER.md"
                    path.write_text(path.read_text(encoding="utf-8").replace("- state: resolved", "- state: open"), encoding="utf-8")
                    expected = "DQ material open/blocked impede conclusão"
                self.assert_no_go(expected)

    def test_committed_go_and_blocked_fixtures(self) -> None:
        go = run_audit(FIXTURES / "go-project")
        blocked = run_audit(FIXTURES / "blocked-project")
        self.assertEqual(go.returncode, 0, go.stdout + go.stderr)
        self.assertEqual(blocked.returncode, 2, blocked.stdout + blocked.stderr)

    def test_blocked_is_reachable_without_false_handoff(self) -> None:
        shutil.rmtree(self.root)
        self.root.mkdir()
        write_project(self.root, blocked=True)
        result = run_audit(self.root)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("BLOCKED", result.stdout)
        self.assertIn("BL-0001", result.stdout)
        self.assertNotIn("selected-handoff", result.stdout)

    def test_relative_root_is_supported(self) -> None:
        result = run_audit(self.root, relative=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_constitution_and_template_are_required(self) -> None:
        for relative in (".specify/memory/constitution.md", ".specify/templates/constitution-template.md"):
            with self.subTest(relative=relative):
                write_project(self.root)
                (self.root / relative).unlink()
                self.assert_no_go("required input missing")

    def test_constitution_schema_is_fail_closed(self) -> None:
        path = self.root / ".specify/memory/constitution.md"
        mutations = {
            "placeholder": "governance: {{OWNER}}",
            "semver": "version: next",
            "date": "ratified: someday",
            "governance": "governance: ",
        }
        for name, replacement in mutations.items():
            with self.subTest(name=name):
                write_project(self.root)
                text = path.read_text(encoding="utf-8")
                key = replacement.split(":", 1)[0]
                text = re.sub(rf"(?m)^{re.escape(key)}:.*$", replacement, text)
                path.write_text(text, encoding="utf-8")
                self.assertEqual(run_audit(self.root).returncode, 1)

    def test_workflow_marker_and_state_integrity(self) -> None:
        workflow = self.root / "WORKFLOW.md"
        workflow.write_text(workflow.read_text().replace("workflow:v2", "workflow:v3"), encoding="utf-8")
        self.assert_no_go("WORKFLOW: marker/version")
        write_project(self.root)
        state = json.loads((self.root / "state.json").read_text())
        state["workflow"]["sha256"] = "0" * 64
        (self.root / "state.json").write_text(json.dumps(state))
        self.assert_no_go("workflow hash divergence")

    def test_ready_cardinality_and_position(self) -> None:
        roadmap = self.root / "ROADMAP.md"
        roadmap.write_text(roadmap.read_text().replace("- state: planned", "- state: ready-for-specify"), encoding="utf-8")
        self.assert_no_go("duas ready")
        write_project(self.root)
        roadmap.write_text(roadmap.read_text().replace("- state: ready-for-specify", "- state: planned", 1), encoding="utf-8")
        self.assert_no_go("zero ready")

    def test_execution_order_and_dependencies(self) -> None:
        roadmap = self.root / "ROADMAP.md"
        roadmap.write_text(roadmap.read_text().replace("FASE-001, FASE-002", "FASE-002, FASE-001"), encoding="utf-8")
        self.assert_no_go("ordem não topológica")
        write_project(self.root)
        roadmap.write_text(roadmap.read_text().replace("FASE-001, FASE-002", "FASE-001, FASE-001"), encoding="utf-8")
        self.assert_no_go("execution-order")

    def test_backlog_duplicate_orphan_invalid_and_ready_open(self) -> None:
        backlog = self.root / "DECISION-BACKLOG.md"
        roadmap = self.root / "ROADMAP.md"
        cases = []
        cases.append(("duplicate", lambda: backlog.write_text(backlog.read_text() + backlog.read_text().split("# Decision Backlog\n", 1)[1]), "duplicate"))
        cases.append(("orphan", lambda: roadmap.write_text(roadmap.read_text().replace("BLs: none", "BLs: BL-9999", 1)), "BL orphan"))
        cases.append(("invalid", lambda: backlog.write_text(backlog.read_text().replace("state: resolved", "state: waiting")), "state inválido"))
        for name, mutate, expected in cases:
            with self.subTest(name=name):
                write_project(self.root)
                mutate()
                self.assert_no_go(expected)
        shutil.rmtree(self.root)
        self.root.mkdir()
        write_project(self.root, blocked=True)
        roadmap = self.root / "ROADMAP.md"
        roadmap.write_text(roadmap.read_text().replace("state: blocked", "state: ready-for-specify", 1))
        handoff = self.root / "handoffs/FASE-001-SPECIFY-HANDOFF.md"
        handoff.write_text(handoff.read_text().replace("state: blocked", "state: ready-for-specify", 1))
        frontier = self.root / "DECISION-FRONTIER.md"
        frontier.write_text(frontier.read_text().replace("state: blocked", "state: resolved").replace("final-ref: BL-0001", "final-ref: ADR-0001"))
        round_log = self.root / "ROUND-LOG.jsonl"
        round_log.write_text(round_log.read_text().replace('"transition": "blocked"', '"transition": "resolved"'))
        state_path = self.root / "state.json"
        state = json.loads(state_path.read_text())
        state.update(status="ready", audit_verdict="pending")
        state_path.write_text(json.dumps(state))
        self.assert_no_go("ready ligada a BL open")

    def test_handoff_path_traversal_and_duplicate(self) -> None:
        roadmap = self.root / "ROADMAP.md"
        roadmap.write_text(roadmap.read_text().replace("handoffs/FASE-001", "../FASE-001"), encoding="utf-8")
        self.assert_no_go("path escapes")
        write_project(self.root)
        roadmap = self.root / "ROADMAP.md"
        roadmap.write_text(roadmap.read_text().replace("handoffs/FASE-002-SPECIFY-HANDOFF.md", "handoffs/FASE-001-SPECIFY-HANDOFF.md"), encoding="utf-8")
        self.assert_no_go("handoff duplicado")

    @unittest.skipUnless(SYMLINK_SUPPORTED, "symlink creation is unavailable")
    def test_handoff_symlink_is_rejected(self) -> None:
        roadmap = self.root / "ROADMAP.md"
        target = self.root / "handoffs/FASE-001-SPECIFY-HANDOFF.md"
        link = self.root / "handoffs/link.md"
        link.symlink_to(target)
        roadmap.write_text(roadmap.read_text().replace("handoffs/FASE-001-SPECIFY-HANDOFF.md", "handoffs/link.md"), encoding="utf-8")
        self.assert_no_go("symlink")

    def test_handoff_triad_and_technical_content(self) -> None:
        handoff = self.root / "handoffs/FASE-001-SPECIFY-HANDOFF.md"
        mutations = {
            "phase": ("- phase: FASE-001", "- phase: FASE-002", "phase divergence"),
            "context": ("- context-refs: API", "- context-refs: Missing", "context divergence"),
            "adr": ("- ADRs: ADR-0001", "- ADRs: none", "ADR divergence"),
            "heading": ("## WHAT", "## Stack\nPython\n\n## WHAT", "heading técnico"),
            "field": ("- state:", "- stack: Python\n- state:", "campo técnico"),
        }
        for name, (old, new, expected) in mutations.items():
            with self.subTest(name=name):
                write_project(self.root)
                handoff.write_text(handoff.read_text().replace(old, new, 1), encoding="utf-8")
                self.assert_no_go(expected)

    def test_plan_context_triad_how_and_selected_handoff(self) -> None:
        plan = self.root / "PLAN-CONTEXT.md"
        mutations = {
            "phase": ("- phase: FASE-001", "- phase: FASE-002", "phase divergence"),
            "adr": ("- ADRs: ADR-0001", "- ADRs: none", "ADR divergence"),
            "how": ("### HOW", "### DESIGN", "HOW vazio/ausente"),
            "selected": ("# Plan Context", "selected-handoff: x\n# Plan Context", "selected-handoff"),
        }
        for name, (old, new, expected) in mutations.items():
            with self.subTest(name=name):
                write_project(self.root)
                plan.write_text(plan.read_text().replace(old, new, 1), encoding="utf-8")
                self.assert_no_go(expected)

    def test_legacy_managed_paths(self) -> None:
        legacy = self.root / "adrs"
        legacy.mkdir()
        (legacy / "ADR-0002.md").write_text("x")
        self.assert_no_go("adrs legado")

    @unittest.skipUnless(SYMLINK_SUPPORTED, "symlink creation is unavailable")
    def test_symlinked_managed_path_is_rejected(self) -> None:
        workflow = self.root / "WORKFLOW.md"
        outside = self.root / "outside.md"
        outside.write_text(workflow.read_text())
        workflow.unlink()
        workflow.symlink_to(outside)
        self.assert_no_go("symlink")

    def test_state_required_fields_paths_hashes_limits_and_second_pass(self) -> None:
        state_path = self.root / "state.json"
        mutations = {
            "missing": lambda state: state.pop("workflow"),
            "path": lambda state: state["constitution"].update(path="elsewhere"),
            "hash": lambda state: state["constitution"].update(sha256="bad"),
            "limits": lambda state: state.update(limits={}),
            "second": lambda state: state.update(second_pass={"new_material_dqs": 1}),
            "milestone-invalid": lambda state: state.update(milestone_status="done"),
            "milestone-premature": lambda state: state.update(milestone_status="completed"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                write_project(self.root)
                state = json.loads(state_path.read_text())
                mutate(state)
                state_path.write_text(json.dumps(state))
                self.assertEqual(run_audit(self.root).returncode, 1)

    def test_frontier_and_round_log_are_validated(self) -> None:
        frontier = self.root / "DECISION-FRONTIER.md"
        frontier.write_text(frontier.read_text().replace("state: resolved", "state: open"), encoding="utf-8")
        self.assert_no_go("DQ material open/blocked")
        write_project(self.root)
        (self.root / "ROUND-LOG.jsonl").write_text('{"round_id":"bad"}\n')
        self.assert_no_go("round_id inválido")

    def test_adr_schema_is_validated(self) -> None:
        adr = self.root / "docs/adr/ADR-0001.md"
        adr.write_text("status: accepted\nevidence-status: unverified\n")
        self.assert_no_go("sources ausente")

    def test_invalid_utf8_is_deterministic_no_go_without_traceback(self) -> None:
        (self.root / "CONTEXT.md").write_bytes(b"\xff\xfe")
        result = run_audit(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "NO-GO\n- invalid UTF-8 input\n")
        self.assertNotIn("Traceback", result.stderr)

    def test_v2_separates_artifacts_and_project_governance(self) -> None:
        artifact = self.root / "artifacts"
        project = self.root / "project"
        shutil.copytree(self.root, artifact, ignore=shutil.ignore_patterns("artifacts", "project", ".specify", "WORKFLOW.md"))
        project.mkdir()
        (project / "WORKFLOW.md").write_text(WORKFLOW_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
        state = json.loads((artifact / "state.json").read_text())
        state["workflow"]["path"] = "WORKFLOW.md"
        state["workflow"]["sha256"] = sha256(project / "WORKFLOW.md")
        (artifact / "state.json").write_text(json.dumps(state))
        result = subprocess.run([sys.executable, str(AUDITOR), str(artifact), "--project-root", str(project), "--json"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["verdict"], "GO")

    def test_v2_governance_hash_and_utf8_are_fail_closed(self) -> None:
        artifact = self.root / "artifacts"
        project = self.root / "project"
        shutil.copytree(self.root, artifact, ignore=shutil.ignore_patterns("artifacts", "project"))
        project.mkdir()
        workflow = project / "WORKFLOW.md"
        workflow.write_text(WORKFLOW_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
        state = json.loads((artifact / "state.json").read_text())
        state["workflow"]["path"] = "WORKFLOW.md"
        state["workflow"]["sha256"] = "0" * 64
        (artifact / "state.json").write_text(json.dumps(state))
        result = subprocess.run([sys.executable, str(AUDITOR), str(artifact), "--project-root", str(project), "--json"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["verdict"], "NO-GO")
        (artifact / "CONTEXT.md").write_bytes(b"\xff")
        result = subprocess.run([sys.executable, str(AUDITOR), str(artifact), "--project-root", str(project), "--json"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["code"], "INVALID-UTF8")
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
