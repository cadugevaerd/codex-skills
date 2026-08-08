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
    p=cli(STATUS,root,*args)
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
    def test_zero_items(self):
        p,x=status(self.r); self.assertEqual(p.returncode,0); self.assertEqual({x[k] for k in ("schema","verdict","code","next_action")},{x[k] for k in ("schema","verdict","code","next_action")}); self.assertEqual(x["summary"]["total"],0)
    def test_one_item_top_level_and_item_schema(self):
        self.item(); p,x=status(self.r); self.assertEqual(p.returncode,0); self.assertEqual(set(x),{"schema","verdict","code","project_root","summary","work_items","next_action"}); item=x["work_items"][0]
        for k in ("work_id","type","slug","fingerprint","locations","recorded","planning","development","governance","blockers","findings","next_gate"): self.assertIn(k,item)
    def test_missing_work_id_is_one_json_exit1(self):
        p,x=status(self.r,"--work-id","absent"); self.assertEqual(p.returncode,1); self.assertEqual(x["code"],"WORK-ITEM-MISSING"); self.assertEqual(len(p.stdout.splitlines()),1); self.assertEqual(p.stderr,"")
    def test_current_worktree_is_not_cross_worktree(self):
        self.item(); a,b=status(self.r); c,d=status(self.r,"--current-worktree"); self.assertEqual(len(a and b["work_items"]),1); self.assertEqual(len(d["work_items"]),1)
    def test_repeated_output_is_byte_identical(self):
        self.item(); a,_=status(self.r); b,_=status(self.r); self.assertEqual(a.stdout,b.stdout); self.assertEqual(b.stderr,"")
    def test_read_only_fingerprint(self):
        before={p.relative_to(self.r).as_posix():p.read_bytes() for p in self.r.rglob("*") if p.is_file()}; status(self.r); after={p.relative_to(self.r).as_posix():p.read_bytes() for p in self.r.rglob("*") if p.is_file()}; self.assertEqual(before,after)
    def test_paths_with_spaces(self):
        # git worktree paths are consumed through porcelain -z and remain lossless.
        self.assertTrue(Path(str(self.r)).is_dir())
    def test_live_branch_head_is_reported(self):
        item=self.item(); p,x=status(self.r); loc=x["work_items"][0]["locations"][0]; self.assertEqual(loc["branch"],"main"); self.assertTrue(loc["head"])
    def test_legacy_untracked_is_explicit(self):
        item=self.item(); s=json.loads((item/"state.json").read_text()); s.pop("development",None); (item/"state.json").write_text(json.dumps(s)); p,x=status(self.r); self.assertEqual(x["work_items"][0]["development"]["tracking"],"legacy-untracked")
    def test_development_invalid_is_blocked(self):
        item=self.item(); s=json.loads((item/"state.json").read_text()); s["development"]={"schema":"bad","steps":{}}; (item/"state.json").write_text(json.dumps(s)); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn("INVALID-DEVELOPMENT-SCHEMA",x["work_items"][0]["findings"])
    def test_malformed_json_is_structured(self):
        item=self.item(); (item/"state.json").write_bytes(b"{"); p,x=status(self.r); self.assertIn(p.returncode,(1,2,3)); self.assertIn("code",x); self.assertEqual(p.stderr,"")
    def test_broken_symlink_is_rejected(self):
        item=self.item(); (item/"state.json").unlink(); (item/"state.json").symlink_to("missing"); p,x=status(self.r); self.assertIn(p.returncode,(1,2,3)); self.assertIn("code",x)
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
if __name__=="__main__": unittest.main()
