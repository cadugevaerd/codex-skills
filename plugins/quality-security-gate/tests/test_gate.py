#!/usr/bin/env python3
import hashlib, json, re, subprocess, tempfile, tomllib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLUGIN = ROOT / "plugins/quality-security-gate"
CLI = PLUGIN / "scripts/quality_gatectl.py"
HOOK = PLUGIN / "scripts/project_context_hook.py"
MODS = [f"MOD-{i:03d}" for i in range(1, 13)]
OWNERS = {
    "GATE-001": {"MOD-001", "MOD-012"}, "GATE-002": {"MOD-003"},
    "GATE-003": {"MOD-002", "MOD-004"},
    "GATE-004": {f"MOD-{i:03d}" for i in range(5, 11)},
    "GATE-005": {"MOD-010", "MOD-011", "MOD-012"},
}


def ev(label):
    return {"source_type": "file", "source": "fixture", "locator": f"controls/{label}:1",
            "digest": hashlib.sha256(label.encode()).hexdigest(), "observed": f"verified {label}"}


def digest_tree(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.is_symlink() and ".git" not in p.parts:
            h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


class GateV2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.base = Path(self.tmp.name); self.repo = self.base / "repo"; self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Test"], check=True)
        (self.repo / "README.md").write_text("fixture\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "fixture"], check=True)

    def tearDown(self): self.tmp.cleanup()

    def run_cli(self, cmd, data=None, markdown=False, root=None):
        argv = ["python3", str(CLI), cmd, "--root", str(root or self.repo)]
        if data is not None:
            p = self.base / f"{cmd}.json"; p.write_text(json.dumps(data)); argv += ["--input", str(p)]
        if not markdown: argv.append("--json")
        return subprocess.run(argv, text=True, capture_output=True)

    def payload(self, result):
        self.assertEqual(len(result.stdout.strip().splitlines()), 1, result.stderr)
        return json.loads(result.stdout)

    def plan(self): return self.payload(self.run_cli("plan"))

    def results(self, snapshot, outcome="PASS", state="AUTOMATED_ENFORCED"):
        rows = []
        for mid in MODS:
            gates = sorted(g for g, owners in OWNERS.items() if mid in owners)
            finding = None if outcome != "FAIL" else {
                "id": f"{mid}-F001", "severity": "HIGH", "summary": "control failed",
                "cause": "fixture control absent", "impact": "gate cannot be enforced"}
            rows.append({"module_id": mid, "snapshot": snapshot, "outcome": outcome,
                "automation_state": state, "evidence": [ev(mid)],
                "gates": [{"id": g, "outcome": outcome, "automation_state": state,
                           "evidence": [ev(f"{g}-{mid}")]} for g in gates],
                "finding": finding,
                "correction": {"target": f"controls/{mid}", "action": f"Implement {mid}",
                    "acceptance": f"{mid} passes enforced",
                    "post_fix_validation": {"status": "NOT_RUN", "procedure": [f"Re-run {mid}"]}}})
        return {"module_results": rows}

    def test_plan_contract_and_exact_tasks(self):
        p = self.plan(); self.assertEqual((p["schema_version"], p["plugin_version"]), ("2.0", "0.2.0"))
        self.assertEqual([m["id"] for m in p["modules"]], MODS); self.assertEqual([t["module_id"] for t in p["investigator_tasks"]], MODS)
        for t in p["investigator_tasks"]: self.assertTrue(t["read_only"] and t["strict_json"] and t["capabilities"] == ["read_files", "list_files"])

    def test_deterministic_risk_and_gate_sets(self):
        p1 = self.plan(); (self.repo / "Dockerfile").write_text("FROM scratch\n"); p2 = self.plan()
        (self.repo / "AGENTS.md").write_text("Production public API IAM personal data\n"); p3 = self.plan()
        self.assertEqual([p1["risk"]["profile"], p2["risk"]["profile"], p3["risk"]["profile"]], ["P1", "P2", "P3"])
        self.assertEqual(list(map(lambda x: len(x["required_gates"]), (p1, p2, p3))), [3, 4, 5])

    def test_exact_agent_packaging_is_read_only(self):
        markdown = sorted((PLUGIN / "agents").glob("quality-security-gate-mod-*.md"))
        toml = sorted((PLUGIN / "agents").glob("quality-security-gate-mod-*.toml"))
        self.assertIn((len(markdown), len(toml)), {(12, 0), (0, 12)})
        paths = markdown or toml
        self.assertEqual([p.stem[-7:].upper() for p in paths], MODS)
        names = []
        for mid, p in zip(MODS, paths):
            text = p.read_text(); self.assertIn(mid, text.upper())
            if markdown:
                names.append(re.search(r"^name:\s*(\S+)", text, re.M).group(1))
                self.assertIn("quality-security-gate:quality-security-gate", text); self.assertIn("isolation: worktree", text)
                tools = re.search(r"^tools:\s*(.+)$", text, re.M).group(1); self.assertNotIn("Write", tools); self.assertNotIn("Edit", tools)
            else:
                agent = tomllib.loads(text); names.append(agent["name"])
                self.assertEqual(agent["sandbox_mode"], "read-only")
                self.assertIn("quality-security-gate-knowledge", agent["developer_instructions"])
        self.assertEqual(len(set(names)), 12)

    def test_manifests_schemas_and_docs_are_complete(self):
        paths = list(PLUGIN.rglob("*.json")); self.assertGreaterEqual(len(paths), 3)
        self.assertTrue((PLUGIN / "schemas/module-result.schema.json").is_file())
        self.assertTrue((PLUGIN / "schemas/consolidated-report.schema.json").is_file())
        for p in paths: json.loads(p.read_text())
        schema = json.loads((PLUGIN / "schemas/module-result.schema.json").read_text()); pattern = schema["properties"]["module_id"]["pattern"]
        self.assertTrue(all(re.fullmatch(pattern, m) for m in MODS)); self.assertFalse(any(re.fullmatch(pattern, m) for m in ("MOD-000", "MOD-013", "MOD-001-x")))
        docs = (PLUGIN / "references/modules.md").read_text() + (PLUGIN / "references/gate-catalog.md").read_text()
        self.assertTrue(all(x in docs for x in MODS + list(OWNERS)))

    def test_go_requires_complete_enforced_current_evidence(self):
        p = self.plan(); r = self.run_cli("consolidate", self.results(p["snapshot"])); self.assertEqual((r.returncode, self.payload(r)["verdict"]), (0, "GO"))

    def test_blocked_and_unknown_take_precedence(self):
        p = self.plan(); d = self.results(p["snapshot"]); row = d["module_results"][4]; row.update(outcome="BLOCKED", automation_state="UNKNOWN")
        for g in row["gates"]: g.update(outcome="BLOCKED", automation_state="UNKNOWN")
        r = self.run_cli("consolidate", d); self.assertEqual((r.returncode, self.payload(r)["verdict"]), (2, "BLOCKED"))

    def test_na_needs_proof_and_cannot_replace_required_gate(self):
        p = self.plan(); d = self.results(p["snapshot"]); row = d["module_results"][4]; row.update(outcome="N/A", automation_state="ABSENT")
        for g in row["gates"]: g.update(outcome="N/A", automation_state="ABSENT")
        self.assertEqual(self.payload(self.run_cli("consolidate", d))["verdict"], "BLOCKED")
        proof = {"status": "NOT_APPLICABLE", "rationale": "P1 has no deployment surface", "evidence": [ev("na-proof")]}; row["applicability"] = proof
        self.assertEqual(self.payload(self.run_cli("consolidate", d))["verdict"], "GO")
        d = self.results(p["snapshot"]); row = d["module_results"][0]; row.update(outcome="N/A", automation_state="ABSENT", applicability=proof)
        for g in row["gates"]: g.update(outcome="N/A", automation_state="ABSENT")
        self.assertEqual(self.payload(self.run_cli("consolidate", d))["verdict"], "BLOCKED")

    def test_gate_owner_mapping_and_coverage_are_enforced(self):
        p = self.plan(); d = self.results(p["snapshot"]); d["module_results"][2]["gates"].append({"id": "GATE-005", "outcome": "PASS", "automation_state": "AUTOMATED_ENFORCED", "evidence": [ev("wrong")]})
        self.assertEqual(self.payload(self.run_cli("consolidate", d))["verdict"], "BLOCKED")
        d = self.results(p["snapshot"]); d["module_results"][0]["gates"] = []
        self.assertEqual(self.payload(self.run_cli("consolidate", d))["verdict"], "BLOCKED")

    def test_confirmed_fail_is_actionable_no_go(self):
        p = self.plan(); d = self.results(p["snapshot"]); d["module_results"][0] = self.results(p["snapshot"], "FAIL", "ABSENT")["module_results"][0]
        r = self.run_cli("consolidate", d); out = self.payload(r); self.assertEqual((r.returncode, out["verdict"]), (1, "NO-GO"))
        row = out["modules"][0]; self.assertTrue(row["finding"]["cause"] and row["correction"]["target"] and row["correction"]["action"] and row["correction"]["acceptance"])
        self.assertEqual(row["correction"]["post_fix_validation"]["status"], "NOT_RUN")

    def test_malformed_stale_duplicate_and_weak_evidence_block(self):
        p = self.plan(); self.assertEqual(self.payload(self.run_cli("consolidate", []))["verdict"], "BLOCKED")
        variants = []
        d = self.results(p["snapshot"]); d["module_results"].pop(); variants.append(d)
        d = self.results(p["snapshot"]); d["module_results"][0]["snapshot"] = {"fingerprint": "bad"}; variants.append(d)
        d = self.results(p["snapshot"]); d["module_results"][-1]["module_id"] = "MOD-001"; variants.append(d)
        d = self.results(p["snapshot"]); d["module_results"][0]["evidence"] = ["invented"]; variants.append(d)
        d = self.results(p["snapshot"]); d["module_results"][0]["gates"] *= 2; variants.append(d)
        for item in variants: self.assertEqual(self.payload(self.run_cli("consolidate", item))["verdict"], "BLOCKED")

    def test_markdown_always_has_gate000_and_twelve_modules(self):
        p = self.plan(); r = self.run_cli("report", self.results(p["snapshot"]), markdown=True); self.assertEqual(r.returncode, 0)
        self.assertTrue(all(x in r.stdout.splitlines()[0] for x in ("Gate", "Automation", "Evidence", "Critério de aceite", "Validação")))
        rows = r.stdout.splitlines()[2:]; self.assertEqual(len(rows), 13); self.assertIn("GATE-000", rows[0])

    def test_global_failure_keeps_all_rows_and_machine_code(self):
        r = self.run_cli("plan", root=self.base / "missing"); out = self.payload(r); self.assertEqual((r.returncode, out["verdict"]), (2, "BLOCKED")); self.assertEqual([m["id"] for m in out["modules"]], MODS)
        usage = subprocess.run(["python3", str(CLI), "plan", "--json"], text=True, capture_output=True); self.assertEqual(usage.returncode, 3); self.payload(usage)

    def test_all_commands_leave_target_byte_identical(self):
        before = (digest_tree(self.repo), subprocess.check_output(["git", "-C", str(self.repo), "status", "--porcelain"], text=True)); p = self.plan(); data = self.results(p["snapshot"])
        for cmd in ("plan", "analyze", "status"): self.run_cli(cmd)
        self.run_cli("consolidate", data); self.run_cli("report", data, markdown=True)
        after = (digest_tree(self.repo), subprocess.check_output(["git", "-C", str(self.repo), "status", "--porcelain"], text=True)); self.assertEqual(before, after); self.assertFalse((self.repo / ".quality-gate").exists())

    def test_hook_is_read_only_nested_aware_and_fail_closed(self):
        before = digest_tree(self.repo)
        for raw in ("{}", '{"cwd":"relative"}', "not-json"):
            r = subprocess.run(["python3", str(HOOK)], input=raw, text=True, capture_output=True); self.assertIn("BLOCKED", json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"])
        nested = self.repo / "a/b"; nested.mkdir(parents=True); r = subprocess.run(["python3", str(HOOK)], input=json.dumps({"cwd": str(nested)}), text=True, capture_output=True)
        context = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]; self.assertIn(f"root={self.repo.resolve()}", context); self.assertRegex(context, r"snapshot=[0-9a-f]{64}"); self.assertEqual(digest_tree(self.repo), before)

    def test_symlinked_instruction_fails_closed(self):
        external = self.base / "outside"; external.write_text("production"); (self.repo / "AGENTS.md").symlink_to(external); out = self.plan(); self.assertEqual(out["verdict"], "BLOCKED")
        self.assertEqual(next(x["status"] for x in out["snapshot"]["instructions"] if x["path"] == "AGENTS.md"), "unreadable")

    def test_hook_schema_and_plugin_version_are_packaged(self):
        if (PLUGIN / ".claude-plugin/plugin.json").exists():
            hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text()); self.assertIsInstance(hooks["hooks"]["SessionStart"][0]["hooks"], list); self.assertIsInstance(hooks["hooks"]["SubagentStart"][0]["hooks"], list)
            manifest = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
        else:
            self.assertFalse((PLUGIN / "hooks").exists())
            manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(manifest["version"], "0.2.0")


if __name__ == "__main__": unittest.main()
