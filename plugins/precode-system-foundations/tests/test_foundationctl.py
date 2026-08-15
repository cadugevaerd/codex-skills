import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CLI = ROOT / "scripts" / "foundationctl.py"
VALID = ROOT / "templates" / "foundation.json"


def run(*args):
    return subprocess.run(["python3", str(CLI), *map(str, args)], text=True, capture_output=True)


class FoundationCtlTests(unittest.TestCase):
    def test_init_validate_patch_and_audit(self):
        with tempfile.TemporaryDirectory() as d:
            plan = Path(d) / "foundation.json"
            self.assertEqual(run("init", plan, "--project", "Acme").returncode, 0)
            self.assertTrue(json.loads(run("validate", plan).stdout)["valid"])
            patch = Path(d) / "patch.json"
            patch.write_text(json.dumps([{"op": "replace", "path": "/project/name", "value": "Acme 2"}]))
            self.assertEqual(run("apply-patch", plan, patch).returncode, 0)
            data = json.loads(plan.read_text())
            self.assertEqual(data["project"]["name"], "Acme 2")
            self.assertEqual(len(data["change_log"]), 1)

    def test_invalid_patch_is_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            plan = Path(d) / "foundation.json"
            plan.write_text(VALID.read_text())
            before = plan.read_bytes()
            patch = Path(d) / "bad.json"
            patch.write_text(json.dumps([{"op": "replace", "path": "/modules/0/id", "value": "bad"}]))
            self.assertNotEqual(run("apply-patch", plan, patch).returncode, 0)
            self.assertEqual(plan.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
