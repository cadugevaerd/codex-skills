#!/usr/bin/env python3
"""Contract smoke matrix for the persistent eleven-step checkpoint ledger."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'skills/grill-with-docs/scripts/grill_workspace.py'
TEMPLATE=Path(__file__).resolve().parents[1]/'skills/grill-with-docs/assets/WORKFLOW.template.md'
STEPS=['specify','plan','checklist','tasks','analyze','agent-assign','agent-execute','converge','verify','review','ship']

def run(*a): return subprocess.run([sys.executable,str(SCRIPT),*map(str,a)],text=True,capture_output=True)
class CheckpointContract(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.r=Path(self.t.name); subprocess.run(['git','init','-q','-b','main',str(self.r)],check=True); (self.r/'WORKFLOW.md').write_bytes(TEMPLATE.read_bytes()); subprocess.run(['git','-C',str(self.r),'add','.','&&'],capture_output=True)
  subprocess.run(['git','-C',str(self.r),'add','.'],check=True); subprocess.run(['git','-C',str(self.r),'config','user.email','t@e']); subprocess.run(['git','-C',str(self.r),'config','user.name','t']); subprocess.run(['git','-C',str(self.r),'commit','-qm','init']);
  self.assertEqual(run('init',self.r,'--type','feature','--slug','x','--work-id','wx').returncode,0); (self.r/'e').write_text('e')
 def tearDown(self): self.t.cleanup()
 def call(self,step,state,**kw):
  a=['checkpoint',self.r,'--work-id','wx','--step',step,'--state',state]
  for x in kw.get('evidence',[]): a += ['--evidence',x]
  if 'reason' in kw: a += ['--reason',kw['reason']]
  return run(*a)
 def test_full_matrix_persists(self):
  for s in STEPS:
   self.assertEqual(self.call(s,'in-progress').returncode,0,s)
   self.assertEqual(self.call(s,'complete',evidence=['e']).returncode,0,s)
  d=json.loads((self.r/'.grill/work-items/wx/state.json').read_text()); self.assertTrue(all(d['development']['steps'][s]=='complete' for s in STEPS)); self.assertEqual(d['development']['current_step'],'ship')
 def test_skip_and_evidence_and_block_reason(self):
  self.assertNotEqual(self.call('plan','in-progress').returncode,0); self.assertNotEqual(self.call('specify','complete').returncode,0); self.assertNotEqual(self.call('specify','blocked').returncode,0)
  self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(self.call('specify','blocked',reason='wait').returncode,0); self.assertEqual(self.call('specify','in-progress').returncode,0)
 def test_reused_and_divergence(self):
  self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(self.call('specify','in-progress',reason='different').returncode,2)
 def test_output_is_one_json_line(self):
  p=self.call('specify','in-progress'); self.assertEqual(len(p.stdout.splitlines()),1); self.assertEqual(p.stderr,''); json.loads(p.stdout)
if __name__=='__main__': unittest.main()
