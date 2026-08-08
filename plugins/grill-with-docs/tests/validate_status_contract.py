#!/usr/bin/env python3
"""Matriz pública do contrato grill_workspace.py status (somente interface CLI)."""
from __future__ import annotations
import concurrent.futures, hashlib, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

PLUGIN=Path(__file__).resolve().parents[1]
WS=PLUGIN/"skills/grill-with-docs/scripts/grill_workspace.py"
STATUS=PLUGIN/"skills/grill-with-docs/scripts/grill_status.py"

def cli(script,*args):
    return subprocess.run([sys.executable,str(script),*(str(x) for x in args)],text=True,capture_output=True,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
def status(root,*args):
    # Exercise the public CORE entry point; direct grill_status invocation
    # would bypass status governance and timeout handling.
    p=cli(WS,"status",root,*args)
    assert len(p.stdout.splitlines())==1,(p.stdout,p.stderr)
    return p,json.loads(p.stdout)
class StatusPublicContract(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.r=Path(self.t.name)
        subprocess.run(["git","init","-q","-b","main",str(self.r)],check=True)
        for k,v in (("user.email","t@example.invalid"),("user.name","status tests")): subprocess.run(["git","-C",str(self.r),"config",k,v],check=True)
        (self.r/"WORKFLOW.md").write_text("# workflow\n")
        subprocess.run(["git","-C",str(self.r),"add","."],check=True); subprocess.run(["git","-C",str(self.r),"commit","-qm","init"],check=True)
    def tearDown(self): self.t.cleanup()
    def item(self, wid="work-a", root=None):
        root=root or self.r; p=cli(WS,"init",root,"--type","feature","--slug","alpha","--work-id",wid); self.assertEqual(p.returncode,0,p.stderr); return root/".grill/work-items"/wid
    def test_core_entrypoint_zero_items_exact_schema(self):
        p,x=status(self.r); self.assertEqual(p.returncode,0)
        self.assertEqual(x["schema"],"grill-status/v1"); self.assertEqual(x["verdict"],"OK")
        self.assertEqual(x["code"],"EMPTY"); self.assertEqual(x["next_action"],"iniciar")
        self.assertEqual(x["summary"],{"total":0,"in_progress":0,"blocked":0,"completed":0})
    def test_one_item_top_level_and_item_schema(self):
        self.item(); p,x=status(self.r); self.assertEqual(p.returncode,0); self.assertEqual(set(x),{"schema","verdict","code","project_root","summary","work_items","next_action"}); item=x["work_items"][0]
        for k in ("work_id","type","slug","fingerprint","locations","recorded","planning","development","governance","blockers","findings","next_gate"): self.assertIn(k,item)
    def test_missing_work_id_is_one_json_exit1(self):
        p,x=status(self.r,"--work-id","absent"); self.assertEqual(p.returncode,1); self.assertEqual(x["code"],"WORK-ITEM-MISSING"); self.assertEqual(len(p.stdout.splitlines()),1); self.assertEqual(p.stderr,"")
    def test_current_worktree_is_not_cross_worktree(self):
        self.item(); _,b=status(self.r); _,d=status(self.r,"--current-worktree"); self.assertEqual(len(b["work_items"]),1); self.assertEqual(len(d["work_items"]),1)
    def test_repeated_output_is_byte_identical(self):
        self.item(); a,_=status(self.r); b,_=status(self.r); self.assertEqual(a.stdout,b.stdout); self.assertEqual(b.stderr,"")
    def test_read_only_fingerprint(self):
        before={p.relative_to(self.r).as_posix():p.read_bytes() for p in self.r.rglob("*") if p.is_file()}; status(self.r); after={p.relative_to(self.r).as_posix():p.read_bytes() for p in self.r.rglob("*") if p.is_file()}; self.assertEqual(before,after)
    def test_real_worktree_with_spaces_default_aggregates_equal_bundle(self):
        self.item(); secondary=Path(self.t.name)/"secondary worktree"
        subprocess.run(["git","-C",str(self.r),"worktree","add","-b","other",str(secondary)],check=True,capture_output=True)
        target=secondary/".grill/work-items/work-a"; target.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(self.r/".grill/work-items/work-a",target)
        constitution=self.r/".specify/memory/constitution.md"
        if constitution.exists(): (secondary/".specify/memory").mkdir(parents=True,exist_ok=True); shutil.copy2(constitution,secondary/".specify/memory/constitution.md")
        _,x=status(self.r); item=x["work_items"][0]; self.assertEqual(len(item["locations"]),2); self.assertEqual(item["locations"],[*sorted(item["locations"],key=lambda z:(z["worktree"],z["path"]))]); self.assertEqual(len({v["fingerprint"] for v in item.get("variants",[item])}),1)

    def test_current_worktree_excludes_secondary_real_worktree(self):
        self.test_real_worktree_with_spaces_default_aggregates_equal_bundle()
        secondary=Path(self.t.name)/"secondary worktree"; _,main=status(self.r,"--current-worktree"); _,other=status(secondary,"--current-worktree")
        self.assertEqual(len(main["work_items"][0]["locations"]),1); self.assertEqual(len(other["work_items"][0]["locations"]),1); self.assertTrue(other["work_items"][0]["locations"][0]["current"])

    def test_divergent_duplicate_preserves_both_locations(self):
        self.test_real_worktree_with_spaces_default_aggregates_equal_bundle(); secondary=Path(self.t.name)/"secondary worktree"; (secondary/".grill/work-items/work-a/state.json").write_bytes(b'{"status":"divergent"}')
        p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertEqual(x["code"],"DUPLICATE-WORK-ID"); self.assertEqual(len(x["work_items"][0]["locations"]),2); self.assertEqual(len(x["work_items"][0]["variants"]),2)
    def test_live_branch_head_is_reported(self):
        item=self.item(); p,x=status(self.r); loc=x["work_items"][0]["locations"][0]; self.assertEqual(loc["branch"],"main"); self.assertTrue(loc["head"])
    def test_legacy_untracked_is_explicit(self):
        item=self.item(); s=json.loads((item/"state.json").read_text()); s.pop("development",None); (item/"state.json").write_text(json.dumps(s)); p,x=status(self.r); self.assertEqual(x["work_items"][0]["development"]["tracking"],"legacy-untracked")
    def test_development_invalid_is_blocked(self):
        item=self.item(); s=json.loads((item/"state.json").read_text()); s["development"]={"schema":"bad","steps":{}}; (item/"state.json").write_text(json.dumps(s)); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn("INVALID-DEVELOPMENT-SCHEMA",x["work_items"][0]["findings"])
    def test_malformed_state_json_is_exact_exit1(self):
        item=self.item(); (item/"state.json").write_bytes(b"{"); p,x=status(self.r); self.assertEqual(p.returncode,1); self.assertEqual(x["code"],"MALFORMED-JSON"); self.assertEqual(p.stderr,"")

    def test_invalid_utf8_state_is_exact(self):
        item=self.item(); (item/"state.json").write_bytes(b"\xff"); p,x=status(self.r); self.assertEqual(p.returncode,1); self.assertEqual(x["code"],"INVALID-UTF8")

    def test_direct_external_symlink_state_hides_secret(self):
        item=self.item(); secret=Path(self.t.name)/"secret"; secret.write_text("TOP-SECRET"); (item/"state.json").unlink(); (item/"state.json").symlink_to(secret); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-FILE"}); self.assertNotIn("TOP-SECRET",p.stdout)
    def test_broken_symlink_is_rejected(self):
        item=self.item(); (item/"state.json").unlink(); (item/"state.json").symlink_to("missing"); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-FILE"})

    def test_work_item_symlink_is_rejected(self):
        self.item(); outside=Path(self.t.name)/"outside"; outside.mkdir(); d=self.r/".grill/work-items/work-b"; d.symlink_to(outside,target_is_directory=True); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-WORK-ITEM"})

    def test_snapshot_contains_mtimes(self):
        self.item(); _,x=status(self.r); self.assertTrue(x["work_items"][0]["snapshot"]); self.assertIn("mtime_ns",next(iter(x["work_items"][0]["snapshot"].values())))
    def test_concurrent_readers_are_deterministic(self):
        self.item()
        with concurrent.futures.ThreadPoolExecutor(4) as ex: out=list(ex.map(lambda _:status(self.r)[0].stdout,range(8)))
        self.assertEqual(len(set(out)),1)
    def test_fingerprint_is_full_bundle(self):
        item=self.item(); p,x=status(self.r); fp=x["work_items"][0]["fingerprint"]; self.assertEqual(len(fp),64); (item/"extra").write_text("x"); p,y=status(self.r); self.assertNotEqual(fp,y["work_items"][0]["fingerprint"])
    def test_planning_has_public_execution_and_phase_state(self):
        self.item(); _,x=status(self.r); planning=x["work_items"][0]["planning"]; self.assertIn("execution_order",planning); self.assertIn("phases",planning); self.assertIn("phase_state",planning)
    def test_governance_has_receipt_audit_constitution_check(self):
        self.item(); _,x=status(self.r); g=x["work_items"][0]["governance"]; self.assertTrue({"receipt","reconciled"}&set(g)); self.assertIn("audit",g); self.assertIn("constitution",g); self.assertIn("check",g)
    def test_stdout_is_exactly_json_and_stderr_empty(self):
        self.item(); p,_=status(self.r); self.assertEqual(p.stderr,""); json.loads(p.stdout)
    def test_receipt_direct_symlink_is_rejected_without_following(self):
        self.item(); receipts=self.r/".grill/global/receipts"; receipts.mkdir(parents=True,exist_ok=True); secret=Path(self.t.name)/"receipt-secret"; secret.write_text("SECRET"); (receipts/"work-a.json").symlink_to(secret); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-FILE"}); self.assertNotIn("SECRET",p.stdout)
    def test_constitution_external_symlink_is_rejected(self):
        self.item(); path=self.r/".specify/memory/constitution.md"; path.parent.mkdir(parents=True,exist_ok=True); secret=Path(self.t.name)/"constitution-secret"; secret.write_text("SECRET"); path.unlink(missing_ok=True); path.symlink_to(secret); p,x=status(self.r); self.assertEqual(p.returncode,3); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-FILE"}); self.assertNotIn("SECRET",p.stdout)
if __name__=="__main__": unittest.main()
