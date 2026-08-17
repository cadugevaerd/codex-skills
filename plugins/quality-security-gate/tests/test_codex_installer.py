#!/usr/bin/env python3
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
INSTALLER = PLUGIN / "scripts/install_codex_agents.py"
ROLES = {f"quality_security_gate_mod_{i:03d}" for i in range(1, 13)}
FILES = {f"quality-security-gate-mod-{i:03d}.toml" for i in range(1, 13)}


class CodexInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / "codex"
        self.home.mkdir()
        (self.home / "config.toml").write_text('model = "existing"\n', encoding="utf-8")

    def tearDown(self): self.temp.cleanup()

    def run_installer(self, *args):
        return subprocess.run(["python3", str(INSTALLER), "--codex-home", str(self.home), *args], text=True, capture_output=True, check=False)

    def test_install_twice_is_idempotent_and_uninstall_preserves_config(self):
        first = self.run_installer(); self.assertEqual(first.returncode, 0, first.stderr)
        config = self.home / "config.toml"; first_bytes = config.read_bytes(); parsed = tomllib.loads(first_bytes.decode())
        self.assertEqual(set(parsed["agents"]), ROLES); self.assertEqual(parsed["model"], "existing")
        agents_dir = self.home / "agents"
        self.assertEqual({p.name for p in agents_dir.glob("quality-security-gate-mod-*.toml")}, FILES)
        for path in agents_dir.glob("quality-security-gate-mod-*.toml"):
            agent = tomllib.loads(path.read_text()); self.assertEqual(agent["sandbox_mode"], "read-only"); self.assertIn("quality-security-gate-knowledge", agent["developer_instructions"])
        knowledge = agents_dir / "quality-security-gate-knowledge"
        self.assertTrue((knowledge / "skills/quality-security-gate/SKILL.md").is_file()); self.assertTrue((knowledge / "schemas/module-result.schema.json").is_file())
        second = self.run_installer(); self.assertEqual(second.returncode, 0, second.stderr); self.assertEqual(config.read_bytes(), first_bytes)
        self.assertEqual(config.read_text().count("# BEGIN quality-security-gate plugin agents"), 1)
        removed = self.run_installer("--uninstall"); self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertEqual(config.read_text(), 'model = "existing"\n'); self.assertFalse(knowledge.exists())
        self.assertFalse(any((agents_dir / filename).exists() for filename in FILES)); self.assertTrue((self.home / "config.toml.bak-quality-security-gate").is_file())

    def test_conflict_and_tampering_fail_closed(self):
        conflict = self.home / "config.toml"; conflict.write_text('[agents.quality_security_gate_mod_001]\nconfig_file = "other.toml"\n')
        result = self.run_installer(); self.assertEqual(result.returncode, 1); self.assertIn("fora do bloco gerenciado", result.stderr)
        conflict.write_text('model = "existing"\n'); self.assertEqual(self.run_installer().returncode, 0)
        target = self.home / "agents/quality-security-gate-mod-001.toml"; target.write_text(target.read_text() + "# tampered\n")
        result = self.run_installer(); self.assertEqual(result.returncode, 1); self.assertIn("alterado", result.stderr)


if __name__ == "__main__": unittest.main()
