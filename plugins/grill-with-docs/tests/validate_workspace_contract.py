#!/usr/bin/env python3
"""Executable contract matrix for isolated grill workspaces v2."""
from __future__ import annotations

import concurrent.futures
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN / "skills/grill-with-docs/scripts/grill_workspace.py"
WORKFLOW_TEMPLATE = PLUGIN / "skills/grill-with-docs/assets/WORKFLOW.template.md"
CHECK_START = "<!-- grill-constitution-check:start -->"
CHECK_END = "<!-- grill-constitution-check:end -->"


def load_workspace_module():
    name = "grill_workspace_contract_module"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def invoke(*args: object) -> tuple[subprocess.CompletedProcess[str], dict]:
    process = subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    lines = process.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError(f"expected one JSON line, got stdout={process.stdout!r} stderr={process.stderr!r}")
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise AssertionError(process.stdout) from exc
    return process, payload


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True).stdout.strip()


def snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


class WorkspaceV2Contract(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.extra: list[tempfile.TemporaryDirectory] = []
        self._init_repo(self.root)

    def tearDown(self) -> None:
        for temporary in self.extra:
            temporary.cleanup()
        self.temporary.cleanup()

    def _init_repo(self, root: Path) -> None:
        subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
        git(root, "config", "user.email", "tests@example.invalid")
        git(root, "config", "user.name", "Contract Tests")
        (root / "WORKFLOW.md").write_bytes(WORKFLOW_TEMPLATE.read_bytes())
        git(root, "add", "WORKFLOW.md")
        git(root, "commit", "-q", "-m", "initial workflow")

    def _new_repo(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.extra.append(temporary)
        root = Path(temporary.name)
        self._init_repo(root)
        return root

    def _init_item(self, root: Path | None = None, work_id: str = "work-a", kind: str = "feature", slug: str = "alpha") -> Path:
        root = root or self.root
        process, payload = invoke("init", root, "--type", kind, "--slug", slug, "--work-id", work_id)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload["status"], "CREATED")
        return root / ".grill" / "work-items" / work_id

    def _metadata(self, item: Path) -> dict:
        return json.loads((item / "WORK-ITEM.json").read_text(encoding="utf-8"))

    def _write_metadata(self, item: Path, value: dict) -> None:
        (item / "WORK-ITEM.json").write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def _mark_complete(self, item: Path) -> None:
        path = item / "state.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["status"] = "complete"
        value["audit_verdict"] = "GO"
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def _constitution(self, root: Path | None = None) -> Path:
        root = root or self.root
        path = root / ".specify/memory/constitution.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Constitution\n\n"
            "## Core Principles\n\n"
            "### I. Safety First\nAll work MUST fail closed.\n\n"
            "### II. Evidence\nEvery claim MUST have evidence.\n\n"
            "## Governance\nThe constitution is NON-NEGOTIABLE.\n",
            encoding="utf-8",
        )
        return path

    def _read_check(self, item: Path) -> dict:
        text = (item / "CONSTITUTION-CHECK.md").read_text(encoding="utf-8")
        block = text.split(CHECK_START, 1)[1].split(CHECK_END, 1)[0]
        match = re.search(r"```json\s*(\{.*\})\s*```", block, re.DOTALL)
        assert match is not None
        return json.loads(match.group(1))

    def _write_check(self, item: Path, value: dict) -> None:
        text = (
            "# Constitution Check\n\n"
            + CHECK_START
            + "\n```json\n"
            + json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n```\n"
            + CHECK_END
            + "\n"
        )
        (item / "CONSTITUTION-CHECK.md").write_text(text, encoding="utf-8")

    def _approve_check(self, item: Path, status: str = "PASS") -> dict:
        value = self._read_check(item)
        for entry in value["clauses"]:
            entry["status"] = status
            entry["evidence"] = ["tests/evidence.md"]
            entry["justification"] = "verified against the work-item scope"
        self._write_check(item, value)
        return value

    def _set_scope(self, item: Path, paths: list[str]) -> None:
        value = self._metadata(item)
        value["scope"] = {"paths": paths}
        self._write_metadata(item, value)

    def _set_dependencies(self, item: Path, dependencies: list[str]) -> None:
        value = self._metadata(item)
        value["depends-on-work"] = dependencies
        self._write_metadata(item, value)

    def _set_adr_conflicts(self, item: Path, references: list[str]) -> None:
        value = self._metadata(item)
        value["conflicts-with-adrs"] = references
        self._write_metadata(item, value)

    def _commit_all(self, root: Path, message: str = "work item") -> None:
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", message)

    def test_init_isolates_same_slug_and_never_writes_global(self) -> None:
        first = self._init_item(work_id="feature-one", slug="same")
        second = self._init_item(work_id="fix-two", kind="fix", slug="same")
        self.assertNotEqual(first, second)
        self.assertTrue((first / "docs/adr").is_dir())
        self.assertTrue((second / "handoffs").is_dir())
        self.assertFalse((self.root / ".grill/global").exists())
        self.assertEqual((self.root / "WORKFLOW.md").read_bytes(), WORKFLOW_TEMPLATE.read_bytes())
        state = json.loads((first / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["workflow"]["version"], "v2")

    def test_init_reuse_identity_conflict_and_immutable_tamper(self) -> None:
        item = self._init_item(work_id="stable-id")
        process, payload = invoke("init", self.root, "--type", "feature", "--slug", "alpha", "--work-id", "stable-id")
        self.assertEqual((process.returncode, payload["status"]), (0, "REUSED"))
        process, payload = invoke("init", self.root, "--type", "fix", "--slug", "alpha", "--work-id", "stable-id")
        self.assertEqual((process.returncode, payload["code"]), (2, "IDENTITY-DIVERGENCE"))
        metadata = self._metadata(item)
        metadata["immutable"]["slug"] = "tampered"
        self._write_metadata(item, metadata)
        process, payload = invoke("init", self.root, "--type", "feature", "--slug", "alpha", "--work-id", "stable-id")
        self.assertEqual((process.returncode, payload["code"]), (2, "IMMUTABLE-TAMPERED"))

    def test_init_rejects_type_slug_work_id_and_symlink_root(self) -> None:
        for args in (
            ("--type", "task", "--slug", "alpha", "--work-id", "valid-id"),
            ("--type", "feature", "--slug", "../escape", "--work-id", "valid-id"),
            ("--type", "feature", "--slug", "alpha", "--work-id", "../escape"),
        ):
            process, _payload = invoke("init", self.root, *args)
            self.assertEqual(process.returncode, 2)
        outside = self._new_repo()
        (self.root / ".grill").symlink_to(outside, target_is_directory=True)
        process, payload = invoke("init", self.root, "--type", "feature", "--slug", "alpha", "--work-id", "safe-id")
        self.assertEqual((process.returncode, payload["code"]), (2, "SYMLINK-REJECTED"))

    def test_concurrent_same_id_and_automatic_ids_do_not_corrupt(self) -> None:
        command = ("init", self.root, "--type", "feature", "--slug", "parallel", "--work-id", "parallel-id")
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda _index: invoke(*command), range(6)))
        self.assertTrue(all(process.returncode == 0 for process, _payload in results))
        statuses = [payload["status"] for _process, payload in results]
        self.assertEqual(statuses.count("CREATED"), 1)
        self.assertEqual(statuses.count("REUSED"), 5)
        self.assertEqual(len(list((self.root / ".grill/work-items").glob("parallel-id"))), 1)
        automatic = [invoke("init", self.root, "--type", "fix", "--slug", "automatic")[1]["work_id"] for _ in range(4)]
        self.assertEqual(len(set(automatic)), 4)

    def test_audit_without_constitution_is_read_only_and_uses_real_auditor(self) -> None:
        item = self._init_item()
        before = snapshot(item)
        process, payload = invoke("audit", self.root, "--work-id", "work-a")
        self.assertIn(process.returncode, {0, 1, 2})
        self.assertNotEqual(process.returncode, 3)
        self.assertIsNone(payload["constitutional"])
        self.assertIsInstance(payload["audit"], dict)
        self.assertEqual(before, snapshot(item))

    def test_audit_supports_artifact_root_outside_project_root(self) -> None:
        item = self._init_item(work_id="external-artifacts")
        temporary = tempfile.TemporaryDirectory()
        self.extra.append(temporary)
        external = Path(temporary.name) / "arbitrary-directory-name"
        shutil.copytree(item, external)
        before = snapshot(external)
        process, payload = invoke(
            "audit", self.root, "--artifact-root", external, "--project-root", self.root
        )
        self.assertIn(process.returncode, {0, 1, 2})
        self.assertNotEqual(process.returncode, 3)
        self.assertEqual(payload["work_id"], "external-artifacts")
        self.assertEqual(before, snapshot(external))

    def test_constitution_pass_and_not_applicable_are_accepted(self) -> None:
        self._constitution()
        item = self._init_item(work_id="constitutional")
        for status in ("PASS", "NOT-APPLICABLE"):
            self._approve_check(item, status)
            process, payload = invoke("audit", self.root, "--work-id", "constitutional")
            self.assertNotEqual(process.returncode, 3, payload)
            self.assertEqual(payload["constitutional"]["clauses"], 3)

    def test_constitution_rejects_pending_unmapped_blocked_and_violation(self) -> None:
        self._constitution()
        item = self._init_item(work_id="status-gate")
        for status in ("PENDING", "UNMAPPED", "BLOCKED", "VIOLATION"):
            value = self._approve_check(item)
            value["clauses"][0]["status"] = status
            self._write_check(item, value)
            process, payload = invoke("audit", self.root, "--work-id", "status-gate")
            self.assertEqual((process.returncode, payload["verdict"]), (3, "BLOCKED-CONSTITUTION"))

    def test_constitution_rejects_duplicate_missing_evidence_and_justification(self) -> None:
        self._constitution()
        item = self._init_item(work_id="coverage-gate")
        valid = self._approve_check(item)
        variants: list[dict] = []
        duplicate = json.loads(json.dumps(valid)); duplicate["clauses"].append(dict(duplicate["clauses"][0])); variants.append(duplicate)
        missing = json.loads(json.dumps(valid)); missing["clauses"].pop(); variants.append(missing)
        no_evidence = json.loads(json.dumps(valid)); no_evidence["clauses"][0]["evidence"] = []; variants.append(no_evidence)
        no_justification = json.loads(json.dumps(valid)); no_justification["clauses"][0]["justification"] = ""; variants.append(no_justification)
        for value in variants:
            self._write_check(item, value)
            process, _payload = invoke("audit", self.root, "--work-id", "coverage-gate")
            self.assertEqual(process.returncode, 3)

    def test_constitution_rejects_stale_hash_utf8_and_placeholders(self) -> None:
        constitution = self._constitution()
        item = self._init_item(work_id="stale-gate")
        self._approve_check(item)
        constitution.write_text(constitution.read_text(encoding="utf-8") + "\n### III. New Rule\nMUST revalidate.\n", encoding="utf-8")
        process, payload = invoke("audit", self.root, "--work-id", "stale-gate")
        self.assertEqual((process.returncode, payload["code"]), (3, "CONSTITUTION-STALE"))
        other = self._new_repo(); path = other / ".specify/memory/constitution.md"; path.parent.mkdir(parents=True); path.write_bytes(b"\xff")
        process, _payload = invoke("init", other, "--type", "feature", "--slug", "utf", "--work-id", "utf-id")
        self.assertEqual(process.returncode, 3)
        third = self._new_repo(); path = third / ".specify/memory/constitution.md"; path.parent.mkdir(parents=True); path.write_text("# C\n## [PROJECT_PRINCIPLE]\n", encoding="utf-8")
        process, _payload = invoke("init", third, "--type", "feature", "--slug", "placeholder", "--work-id", "placeholder-id")
        self.assertEqual(process.returncode, 3)

    def test_reconcile_source_root_and_real_qualified_ids(self) -> None:
        source = self._new_repo()
        item = self._init_item(source, "source-one")
        self._mark_complete(item)
        (item / "docs/adr/ADR-0042.md").write_text("# ADR-0042\n", encoding="utf-8")
        with (item / "ROUND-LOG.jsonl").open("a", encoding="utf-8") as handle:
            handle.write('{"round_id":"R-0042"}\n')
        process, payload = invoke("reconcile", self.root, "--source-root", source)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "PREVIEW"))
        for qualified in ("source-one/ADR-0042", "source-one/R-0042", "source-one/DQ-0001", "source-one/FASE-001"):
            self.assertIn(qualified, payload["qualified_ids"])
        self.assertNotIn("source-one/BL-0001", payload["qualified_ids"])
        self.assertNotIn("source-one/source-one", payload["qualified_ids"])

    def test_reconcile_source_ref_is_real_repeatable_and_read_only(self) -> None:
        item = self._init_item(work_id="ref-item")
        self._mark_complete(item)
        self._commit_all(self.root, "ref work item")
        shutil.rmtree(self.root / ".grill")
        before = git(self.root, "status", "--porcelain=v1")
        first_process, first = invoke("reconcile", self.root, "--source-ref", "HEAD")
        second_process, second = invoke("reconcile", self.root, "--source-ref", "HEAD")
        self.assertEqual((first_process.returncode, second_process.returncode), (0, 0))
        self.assertEqual(first, second)
        self.assertIn("ref-item", first["work_ids"])
        self.assertFalse((self.root / ".grill").exists())
        self.assertEqual(before, git(self.root, "status", "--porcelain=v1"))

    def test_reconcile_detects_duplicate_divergent_bundle(self) -> None:
        local = self._init_item(work_id="duplicate")
        self._mark_complete(local)
        source = self._new_repo(); remote = self._init_item(source, "duplicate"); self._mark_complete(remote)
        (remote / "ROADMAP.md").write_text("# divergent\n", encoding="utf-8")
        process, payload = invoke("reconcile", self.root, "--source-root", source)
        self.assertEqual(process.returncode, 1)
        self.assertIn("DUPLICATE-WORK-ID:duplicate", payload["conflicts"])

    def test_reconcile_detects_scope_overlap(self) -> None:
        first = self._init_item(work_id="scope-a"); second = self._init_item(work_id="scope-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(second, ["src/service/api.py"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("SCOPE-OVERLAP:") for conflict in payload["conflicts"]))

    def test_reconcile_detects_missing_dependency_and_cycle(self) -> None:
        missing = self._init_item(work_id="missing-dep"); self._mark_complete(missing); self._set_dependencies(missing, ["does-not-exist"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertIn("DEPENDENCY-MISSING:missing-dep->does-not-exist", payload["conflicts"])
        shutil.rmtree(self.root / ".grill")
        first = self._init_item(work_id="cycle-a"); second = self._init_item(work_id="cycle-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_dependencies(first, ["cycle-b"]); self._set_dependencies(second, ["cycle-a"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("DEPENDENCY-CYCLE:") for conflict in payload["conflicts"]))

    def test_reconcile_detects_adr_conflict_invalid_state_and_constitution_stale(self) -> None:
        owner = self._init_item(work_id="adr-owner"); consumer = self._init_item(work_id="adr-consumer", slug="consumer")
        for item in (owner, consumer): self._mark_complete(item)
        (owner / "docs/adr/ADR-0099.md").write_text("# ADR-0099\n", encoding="utf-8")
        self._set_adr_conflicts(consumer, ["adr-owner/ADR-0099"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertIn("ADR-CONFLICT:adr-consumer->adr-owner/ADR-0099", payload["conflicts"])
        state = json.loads((owner / "state.json").read_text(encoding="utf-8")); state["status"] = "in-progress"; (owner / "state.json").write_text(json.dumps(state), encoding="utf-8")
        process, payload = invoke("reconcile", self.root)
        self.assertIn("STATE-NOT-RECONCILABLE:adr-owner", payload["conflicts"])
        self._mark_complete(owner); self._constitution()
        process, payload = invoke("reconcile", self.root)
        self.assertTrue(any(conflict.startswith("CONSTITUTION-STALE:") for conflict in payload["conflicts"]))

    def test_reconcile_apply_rejects_wrong_branch_and_dirty_tree(self) -> None:
        item = self._init_item(); self._mark_complete(item); self._commit_all(self.root)
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "wrong")
        self.assertEqual((process.returncode, payload["code"]), (2, "WRONG-INTEGRATION-BRANCH"))
        (self.root / "dirty.txt").write_text("dirty", encoding="utf-8")
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["code"]), (2, "DIRTY-WORKTREE"))

    def test_reconcile_apply_is_byte_idempotent_without_mtime_churn(self) -> None:
        item = self._init_item(); self._mark_complete(item); self._commit_all(self.root)
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        global_dir = self.root / ".grill/global"
        before = snapshot(global_dir); before_mtime = {path.name: path.stat().st_mtime_ns for path in global_dir.iterdir()}
        time.sleep(0.02)
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "REUSED"))
        self.assertEqual(before, snapshot(global_dir))
        self.assertEqual(before_mtime, {path.name: path.stat().st_mtime_ns for path in global_dir.iterdir()})
        self.assertNotIn(b"\\n", (global_dir / "ROADMAP.md").read_bytes())

    def test_reconcile_concurrent_apply_is_serialized(self) -> None:
        item = self._init_item(); self._mark_complete(item); self._commit_all(self.root)
        command = ("reconcile", self.root, "--apply", "--integration-branch", "main")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _index: invoke(*command), range(4)))
        self.assertTrue(all(process.returncode == 0 for process, _payload in results))
        verdicts = [payload["verdict"] for _process, payload in results]
        self.assertEqual(verdicts.count("APPLIED"), 1)
        self.assertEqual(verdicts.count("REUSED"), 3)
        self.assertEqual(set(snapshot(self.root / ".grill/global")), {"AUDIT.md", "ROADMAP.md"})

    def test_reconcile_concurrent_waiters_recover_one_orphan_lock(self) -> None:
        item = self._init_item(); self._mark_complete(item); self._commit_all(self.root)
        lock = self.root / ".grill/locks/global-reconciliation.lock"
        lock.mkdir(parents=True)
        (lock / "owner.json").write_text(
            json.dumps({"pid": 999_999_999, "host": socket.gethostname(), "process_start": "linux:0"}),
            encoding="utf-8",
        )
        command = ("reconcile", self.root, "--apply", "--integration-branch", "main")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _index: invoke(*command), range(4)))
        self.assertTrue(all(process.returncode == 0 for process, _payload in results))
        verdicts = [payload["verdict"] for _process, payload in results]
        self.assertEqual(verdicts.count("APPLIED"), 1)
        self.assertEqual(verdicts.count("REUSED"), 3)
        self.assertFalse(lock.exists())

    def test_unavailable_process_identity_never_marks_live_lock_stale(self) -> None:
        module = load_workspace_module()
        lock = self.root / "identity.lock"
        lock.mkdir()
        (lock / "owner.json").write_text(
            json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "process_start": "linux:recorded"}),
            encoding="utf-8",
        )
        original = getattr(module, "process_start_observation")
        try:
            setattr(module, "process_start_observation", lambda _pid: ("unavailable", None))
            self.assertFalse(module.stale_local_lock(lock))
            setattr(module, "process_start_observation", lambda _pid: ("found", "linux:reused"))
            self.assertTrue(module.stale_local_lock(lock))
        finally:
            setattr(module, "process_start_observation", original)
            sys.modules.pop("grill_workspace_contract_module", None)

    def test_migrate_preview_apply_preserves_files_directories_and_reuses(self) -> None:
        originals = {
            "CONTEXT.md": b"legacy context\n",
            "ROADMAP.md": b"legacy roadmap\n",
            "docs/adr/ADR-0001.md": b"adr one\n",
            "adrs/ADR-0002.md": b"adr two\n",
            "handoffs/FASE-001.md": b"handoff\n",
        }
        for relative, data in originals.items():
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        process, payload = invoke("migrate", self.root, "--type", "feature", "--slug", "legacy", "--work-id", "migration")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "PREVIEW"))
        self.assertFalse((self.root / ".grill").exists())
        process, payload = invoke("migrate", self.root, "--type", "feature", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        item = self.root / ".grill/work-items/migration"
        expected_destinations = {
            "CONTEXT.md": originals["CONTEXT.md"],
            "ROADMAP.md": originals["ROADMAP.md"],
            "docs/adr/ADR-0001.md": originals["docs/adr/ADR-0001.md"],
            "docs/adr/ADR-0002.md": originals["adrs/ADR-0002.md"],
            "handoffs/FASE-001.md": originals["handoffs/FASE-001.md"],
        }
        for relative, data in expected_destinations.items():
            self.assertEqual((item / relative).read_bytes(), data)
        for relative, data in originals.items():
            self.assertEqual((self.root / relative).read_bytes(), data)
        process, payload = invoke("migrate", self.root, "--type", "feature", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "REUSED"))

    def test_migrate_blocks_divergence_invalid_utf8_and_symlink_without_partial_target(self) -> None:
        (self.root / "CONTEXT.md").write_text("legacy\n", encoding="utf-8")
        process, _payload = invoke("migrate", self.root, "--type", "fix", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual(process.returncode, 0)
        (self.root / ".grill/work-items/migration/CONTEXT.md").write_text("diverged\n", encoding="utf-8")
        process, payload = invoke("migrate", self.root, "--type", "fix", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual((process.returncode, payload["code"]), (2, "TARGET-DIVERGES"))
        invalid = self._new_repo(); (invalid / "CONTEXT.md").write_bytes(b"\xff")
        process, _payload = invoke("migrate", invalid, "--type", "fix", "--slug", "utf", "--work-id", "utf-migration", "--apply")
        self.assertEqual(process.returncode, 1)
        self.assertFalse((invalid / ".grill/work-items/utf-migration").exists())
        linked = self._new_repo(); target = linked / "actual.md"; target.write_text("actual", encoding="utf-8"); (linked / "CONTEXT.md").symlink_to(target)
        process, _payload = invoke("migrate", linked, "--type", "fix", "--slug", "link", "--work-id", "link-migration", "--apply")
        self.assertEqual(process.returncode, 2)
        self.assertFalse((linked / ".grill/work-items/link-migration").exists())

    def test_core_validation_rejects_invalid_metadata_migration_and_adr_reference(self) -> None:
        item = self._init_item(work_id="validation")
        metadata = self._metadata(item)
        metadata["immutable"]["type"] = "task"
        metadata["immutable_sha256"] = "bad"
        self._write_metadata(item, metadata)
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 2)
        self.assertIn(payload["code"], {"IMMUTABLE-TAMPERED", "METADATA-SCHEMA"})

        other = self._new_repo()
        (other / "CONTEXT.md").write_text("legacy\n", encoding="utf-8")
        process, _payload = invoke("migrate", other, "--type", "feature", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual(process.returncode, 0)
        migrated = other / ".grill/work-items/migration/WORK-ITEM.json"
        value = json.loads(migrated.read_text(encoding="utf-8"))
        value["migration"]["source_hashes"]["CONTEXT.md"] = "not-a-sha256"
        migrated.write_text(json.dumps(value), encoding="utf-8")
        process, payload = invoke("reconcile", other)
        self.assertEqual((process.returncode, payload["code"]), (2, "MIGRATION-SCHEMA"))

    def test_constitution_repeated_headings_get_unique_ids(self) -> None:
        constitution = self._constitution()
        constitution.write_text("# C\n## Rules\na\n## Rules\nb\n## Rules\nc\n", encoding="utf-8")
        process, payload = invoke("init", self.root, "--type", "feature", "--slug", "repeat", "--work-id", "repeat")
        self.assertEqual(process.returncode, 0, payload)
        check = self._read_check(self.root / ".grill/work-items/repeat")
        self.assertEqual([entry["id"] for entry in check["clauses"]], ["rules", "rules-2", "rules-3"])

    def test_migrate_does_not_replace_generated_state(self) -> None:
        (self.root / "state.json").write_text('{"status":"legacy"}\n', encoding="utf-8")
        arguments = ("migrate", self.root, "--type", "fix", "--slug", "state", "--work-id", "state-migration", "--apply")
        process, payload = invoke(*arguments)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        target = self.root / ".grill/work-items/state-migration/state.json"
        state = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(state["work_id"], "state-migration")
        self.assertEqual(state["workflow"]["version"], "v2")
        generated = target.read_bytes()
        process, payload = invoke(*arguments)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "REUSED"))
        self.assertEqual(target.read_bytes(), generated)
        self.assertIn("constitution", state)

    def test_migrate_rejects_broken_file_and_directory_symlinks(self) -> None:
        broken_file = self._new_repo()
        (broken_file / "CONTEXT.md").symlink_to(broken_file / "does-not-exist")
        process, payload = invoke(
            "migrate", broken_file, "--type", "fix", "--slug", "broken", "--work-id", "broken-file", "--apply"
        )
        self.assertEqual((process.returncode, payload["code"]), (2, "LEGACY-SYMLINK"))
        self.assertFalse((broken_file / ".grill/work-items/broken-file").exists())
        broken_directory = self._new_repo()
        (broken_directory / "docs").mkdir()
        (broken_directory / "docs/adr").symlink_to(broken_directory / "missing-directory", target_is_directory=True)
        process, payload = invoke(
            "migrate", broken_directory, "--type", "fix", "--slug", "broken", "--work-id", "broken-dir", "--apply"
        )
        self.assertEqual((process.returncode, payload["code"]), (2, "LEGACY-SYMLINK"))
        self.assertFalse((broken_directory / ".grill/work-items/broken-dir").exists())


    def test_hotfix_fast_is_self_contained_and_feature_remains_plan_only(self) -> None:
        args = ("hotfix", self.root, "--slug", "incident", "--scope", "src/auth.py",
                "--reproduction", "curl /login => 500", "--evidence", "incident.log",
                "--correction-test", "tests/auth.py::test_timeout", "--rollback", "revert abc",
                "--constitution-evidence", "not-applicable", "--test-command", f"{sys.executable} -c 'pass'",
                "--work-id", "hotfix-incident")
        process, payload = invoke(*args)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "HOTFIX-PREPARED"))
        item = self.root / ".grill/work-items/hotfix-incident"
        self.assertTrue((item / "HOTFIX.md").is_file())
        audit, audited = invoke("audit", self.root, "--work-id", "hotfix-incident")
        self.assertEqual((audit.returncode, audited["verdict"]), (0, "HOTFIX-PREPARED"))
        go, released = invoke("hotfix-go", self.root, "--work-id", "hotfix-incident")
        self.assertEqual((go.returncode, released["verdict"]), (0, "HOTFIX-GO"))
        self.assertFalse((self.root / ".grill/global").exists())
        bad, bad_payload = invoke("hotfix", self.root, "--slug", "bad", "--scope", "../escape",
                                  "--reproduction", "r", "--evidence", "e", "--correction-test", "t",
                                  "--rollback", "b", "--constitution-evidence", "c", "--test-command", "true")
        self.assertEqual((bad.returncode, bad_payload["code"]), (1, "SCOPE-NOT-CLOSED"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
