#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "plugins/quality-security-gate/scripts/quality_gatectl.py"
HOOK = ROOT / "plugins/quality-security-gate/scripts/project_context_hook.py"
HOOK_CONFIG = ROOT / "plugins/quality-security-gate/hooks/hooks.json"


def run_cli(repo: Path, *args: str):
    return subprocess.run(
        ["python3", str(CLI), *args, "--root", str(repo), "--json"],
        text=True, capture_output=True, check=False,
    )


class QualityGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Test"], check=True)
        (self.repo / "README.md").write_text("# test\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "init"], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self, result):
        self.assertTrue(result.stdout, result.stderr)
        return json.loads(result.stdout)

    def test_init_records_four_absent_paths_and_status_does_not_mutate(self):
        result = run_cli(self.repo, "analyze", "--init")
        self.assertEqual(result.returncode, 1, result.stderr)
        state = self.payload(result)
        self.assertEqual([x["status"] for x in state["instructions"]], ["absent"] * 4)
        state_path = self.repo / ".quality-gate/state.json"
        before = state_path.read_bytes()
        result = run_cli(self.repo, "status")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(before, state_path.read_bytes())

    def test_instruction_change_makes_status_stale(self):
        (self.repo / "AGENTS.md").write_text("initial", encoding="utf-8")
        self.assertEqual(run_cli(self.repo, "analyze", "--init").returncode, 1)
        (self.repo / "AGENTS.md").write_text("changed", encoding="utf-8")
        result = run_cli(self.repo, "status")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(self.payload(result)["stale"])

    def test_risk_increase_and_no_silent_downgrade(self):
        self.assertEqual(run_cli(self.repo, "analyze", "--init").returncode, 1)
        (self.repo / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
        second = self.payload(run_cli(self.repo, "analyze", "--init"))
        self.assertEqual(second["risk"]["computed_level"], "P2")
        self.assertEqual(second["risk"]["accepted_floor"], "P2")
        self.assertTrue(second["risk"]["risk_increase"])
        (self.repo / "Dockerfile").unlink()
        third = self.payload(run_cli(self.repo, "analyze", "--init"))
        self.assertEqual(third["risk"]["computed_level"], "P1")
        self.assertEqual(third["risk"]["effective_level"], "P2")

    def test_instruction_content_can_raise_to_p3(self):
        (self.repo / "AGENTS.md").write_text("This production public API processes personal data.", encoding="utf-8")
        result = self.payload(run_cli(self.repo, "analyze", "--init"))
        self.assertEqual(result["risk"]["computed_level"], "P3")

    def test_malformed_state_is_integrity_error(self):
        q = self.repo / ".quality-gate"
        q.mkdir()
        (q / "state.json").write_text("not-json", encoding="utf-8")
        result = run_cli(self.repo, "status")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(self.payload(result)["verdict"], "USAGE/INTEGRITY")

    def test_symlink_instruction_is_blocked(self):
        target = self.repo / "instruction-target"
        target.write_text("unsafe", encoding="utf-8")
        os.symlink(target.name, self.repo / "AGENTS.md")
        result = run_cli(self.repo, "analyze", "--init")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.payload(result)["verdict"], "BLOCKED")
        self.assertFalse((self.repo / ".quality-gate").exists())

    def test_hook_configuration_wraps_each_event_in_hooks_array(self):
        config = json.loads(HOOK_CONFIG.read_text(encoding="utf-8"))
        for event in ("SessionStart", "SubagentStart"):
            entries = config["hooks"][event]
            self.assertEqual(len(entries), 1)
            self.assertIsInstance(entries[0]["hooks"], list)
            self.assertEqual(entries[0]["hooks"][0]["type"], "command")

    def test_hook_returns_json_without_write(self):
        before = sorted(p.relative_to(self.repo).as_posix() for p in self.repo.rglob("*") if ".git" not in p.parts)
        result = subprocess.run(["python3", str(HOOK), "--hook"], input=json.dumps({"cwd": str(self.repo)}), text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("hookSpecificOutput", payload)
        after = sorted(p.relative_to(self.repo).as_posix() for p in self.repo.rglob("*") if ".git" not in p.parts)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
