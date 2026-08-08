#!/usr/bin/env python3
"""Contract smoke matrix for the persistent eleven-step checkpoint ledger."""
import concurrent.futures, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'skills/grill-with-docs/scripts/grill_workspace.py'
TEMPLATE=Path(__file__).resolve().parents[1]/'skills/grill-with-docs/assets/WORKFLOW.template.md'
STEPS=['specify','plan','checklist','tasks','analyze','agent-assign','agent-execute','converge','verify','review','ship']

def run(*a): return subprocess.run([sys.executable,str(SCRIPT),*map(str,a)],text=True,capture_output=True)
class CheckpointContract(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.r=Path(self.t.name); subprocess.run(['git','init','-q','-b','main',str(self.r)],check=True); (self.r/'WORKFLOW.md').write_bytes(TEMPLATE.read_bytes())
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
  d=json.loads((self.r/'.grill/work-items/wx/state.json').read_text()); self.assertTrue(all(d['development']['steps'][s]=='complete' for s in STEPS)); self.assertEqual(d['development']['current_step'],'complete')
 def test_skip_and_evidence_and_block_reason(self):
  self.assertNotEqual(self.call('plan','in-progress').returncode,0); self.assertNotEqual(self.call('specify','complete').returncode,0); self.assertNotEqual(self.call('specify','blocked').returncode,0)
  self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(self.call('specify','blocked',reason='wait').returncode,0); self.assertEqual(self.call('specify','in-progress').returncode,0)
 def test_reused_and_divergence(self):
  self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(self.call('specify','in-progress',reason='different').returncode,2)
 def test_skip_is_invalid_transition(self): self.assertEqual(self.call('plan','in-progress').returncode,2)
 def test_complete_without_evidence_is_required(self): self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(json.loads(self.call('specify','complete').stdout)['code'],'EVIDENCE-REQUIRED')
 def test_missing_evidence_code(self): self.assertEqual(json.loads(self.call('specify','in-progress').stdout)['verdict'],'UPDATED'); self.assertEqual(json.loads(self.call('specify','complete',evidence=['missing']).stdout)['code'],'EVIDENCE-MISSING')
 def test_directory_evidence_rejected(self): (self.r/'dir').mkdir(); self.call('specify','in-progress'); self.assertEqual(json.loads(self.call('specify','complete',evidence=['dir']).stdout)['code'],'EVIDENCE-NOT-REGULAR')
 def test_blocked_requires_reason(self): self.call('specify','in-progress'); self.assertEqual(json.loads(self.call('specify','blocked').stdout)['code'],'REASON-REQUIRED')
 def test_blocked_retry(self): self.call('specify','in-progress'); self.call('specify','blocked',reason='wait'); self.assertEqual(self.call('specify','in-progress').returncode,0)
 def test_reused_includes_evidence_and_reason(self): self.call('specify','in-progress'); self.call('specify','complete',evidence=['e'],reason='done'); p=self.call('specify','complete',evidence=['e'],reason='done'); self.assertEqual(json.loads(p.stdout)['verdict'],'REUSED')
 def test_divergent_same_state_is_exit_two(self): self.call('specify','in-progress'); p=self.call('specify','in-progress',reason='different'); self.assertEqual(p.returncode,2); self.assertEqual(json.loads(p.stdout)['code'],'STATE-DIVERGENCE')
 def test_current_step_first_pending(self): self.call('specify','in-progress'); p=self.call('specify','complete',evidence=['e']); self.assertEqual(json.loads(p.stdout)['current_step'],'plan')
 def test_ship_gate(self):
  for s in STEPS[:-1]: self.call(s,'in-progress'); self.call(s,'complete',evidence=['e'])
  self.assertEqual(json.loads(self.call('ship','complete',evidence=['e']).stdout)['code'],'INVALID-TRANSITION')
 def test_invalid_step_json(self): p=run('checkpoint',self.r,'--work-id','wx','--step','bad','--state','in-progress'); self.assertEqual(len(p.stdout.splitlines()),1); self.assertEqual(p.stderr,'')
 def test_legacy_requires_explicit_initialization(self): (self.r/'.grill/work-items/wx/state.json').write_text('{}'); p=self.call('specify','in-progress'); self.assertEqual(json.loads(p.stdout)['code'],'LEGACY-UNTRACKED')
 def test_legacy_initialization_requires_from_step(self): (self.r/'.grill/work-items/wx/state.json').write_text('{}'); p=run('checkpoint',self.r,'--work-id','wx','--step','specify','--state','in-progress','--initialize-legacy','--evidence','e','--reason','decide'); self.assertEqual(json.loads(p.stdout)['code'],'LEGACY-INITIALIZATION-REQUIRES-DECISION-EVIDENCE')
 def test_state_unchanged_on_evidence_rejection(self): before=(self.r/'.grill/work-items/wx/state.json').read_bytes(); self.call('specify','in-progress'); before=(self.r/'.grill/work-items/wx/state.json').read_bytes(); self.call('specify','complete',evidence=['missing']); self.assertEqual(before,(self.r/'.grill/work-items/wx/state.json').read_bytes())
 def test_complete_terminal_current_step(self):
  for s in STEPS: self.call(s,'in-progress'); self.call(s,'complete',evidence=['e'])
  self.assertEqual(json.loads((self.r/'.grill/work-items/wx/state.json').read_text())['development']['current_step'],'complete')
 def test_output_contract_all_calls(self):
  p=self.call('specify','in-progress'); self.assertEqual(p.stderr,''); self.assertEqual(len(p.stdout.splitlines()),1); self.assertIsInstance(json.loads(p.stdout),dict)
 def test_invalid_work_id_exact(self):
  p=run('checkpoint',self.r,'--work-id','bad id','--step','specify','--state','in-progress'); self.assertEqual(json.loads(p.stdout)['code'],'INVALID-WORK-ID'); self.assertEqual(p.returncode,2); self.assertEqual(p.stderr,'')
 def test_absolute_evidence_path_exact(self):
  self.call('specify','in-progress'); p=self.call('specify','complete',evidence=[str(self.r/'e')]); self.assertEqual(json.loads(p.stdout)['code'],'INVALID-EVIDENCE-PATH')
 def test_parent_evidence_path_exact(self):
  self.call('specify','in-progress'); p=self.call('specify','complete',evidence=['../e']); self.assertEqual(json.loads(p.stdout)['code'],'INVALID-EVIDENCE-PATH')
 def test_invalid_state_is_structured(self):
  p=run('checkpoint',self.r,'--work-id','wx','--step','specify','--state','bogus'); self.assertEqual(p.returncode,2); self.assertEqual(json.loads(p.stdout)['code'],'INVALID-ARGUMENTS'); self.assertEqual(p.stderr,'')
 def test_global_snapshot_untouched(self):
  g=self.r/'.grill/global'; g.mkdir(parents=True); q=g/'x'; q.write_text('g'); before=(q.read_bytes(),q.stat().st_mtime_ns); self.call('specify','in-progress'); self.assertEqual(before,(q.read_bytes(),q.stat().st_mtime_ns))
 def test_blocked_requires_exact_reason(self):
  self.call('specify','in-progress'); p=self.call('specify','blocked',reason='   '); self.assertEqual(json.loads(p.stdout)['code'],'REASON-REQUIRED')
 def test_evidence_hash_audited(self):
  self.call('specify','in-progress'); p=self.call('specify','complete',evidence=['e']); self.assertEqual(json.loads(p.stdout)['evidence'][0]['sha256'],__import__('hashlib').sha256(b'e').hexdigest())
 def test_missing_work_item_exact(self):
  p=run('checkpoint',self.r,'--work-id','none','--step','specify','--state','in-progress'); self.assertEqual(json.loads(p.stdout)['code'],'WORK-ITEM-MISSING')
 def test_direct_evidence_symlink_is_blocked_without_state_change(self):
  self.call('specify','in-progress'); state=self.r/'.grill/work-items/wx/state.json'; before=(state.read_bytes(),state.stat().st_mtime_ns)
  outside=Path(self.t.name)/'outside-evidence'; outside.write_text('secret'); (self.r/'e-link').symlink_to(outside)
  p=self.call('specify','complete',evidence=['e-link']); self.assertEqual((p.returncode,json.loads(p.stdout)['code']),(2,'EVIDENCE-SYMLINK')); self.assertEqual(before,(state.read_bytes(),state.stat().st_mtime_ns)); self.assertNotIn('secret',p.stdout)
 def test_broken_evidence_symlink_is_blocked(self):
  self.call('specify','in-progress'); (self.r/'broken').symlink_to('missing'); p=self.call('specify','complete',evidence=['broken']); self.assertEqual((p.returncode,json.loads(p.stdout)['code']),(2,'EVIDENCE-SYMLINK'))
 def test_ancestor_evidence_symlink_is_blocked(self):
  self.call('specify','in-progress'); outside=Path(self.t.name)/'outside-dir'; outside.mkdir(); (outside/'proof').write_text('secret'); (self.r/'linked-dir').symlink_to(outside,target_is_directory=True)
  p=self.call('specify','complete',evidence=['linked-dir/proof']); self.assertEqual(p.returncode,2); self.assertEqual(json.loads(p.stdout)['code'],'SYMLINK-REJECTED'); self.assertNotIn('secret',p.stdout)
 def test_concurrent_identical_transition_serializes(self):
  def invoke(_): return self.call('specify','in-progress')
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(invoke,range(2)))
  payloads=[json.loads(p.stdout) for p in results]; self.assertEqual(sorted(p['verdict'] for p in payloads),['REUSED','UPDATED'])
  state=json.loads((self.r/'.grill/work-items/wx/state.json').read_text()); self.assertEqual(len(state['development']['audit']),1); self.assertFalse((self.r/'.grill/work-items/wx.lock').exists())
 def test_concurrent_divergent_transition_is_deterministic(self):
  def invoke(reason): return self.call('specify','in-progress',reason=reason)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(invoke,['one','two']))
  pairs=sorted((p.returncode,json.loads(p.stdout)['verdict']) for p in results); self.assertEqual(pairs,[(0,'UPDATED'),(2,'BLOCKED')])
  state=json.loads((self.r/'.grill/work-items/wx/state.json').read_text()); self.assertEqual(len(state['development']['audit']),1)
 def test_evidence_content_change_causes_state_divergence(self):
  self.call('specify','in-progress'); self.call('specify','complete',evidence=['e'],reason='done'); (self.r/'e').write_text('changed')
  p=self.call('specify','complete',evidence=['e'],reason='done'); self.assertEqual((p.returncode,json.loads(p.stdout)['code']),(2,'STATE-DIVERGENCE'))
 def test_legacy_explicit_specify_initialization_succeeds_without_inference(self):
  path=self.r/'.grill/work-items/wx/state.json'; path.write_text('{}')
  p=run('checkpoint',self.r,'--work-id','wx','--step','specify','--state','in-progress','--initialize-legacy','--from-step','specify','--evidence','e','--reason','explicit-decision')
  self.assertEqual(p.returncode,0,p.stdout); state=json.loads(path.read_text()); self.assertEqual(state['development']['steps']['specify'],'in-progress'); self.assertTrue(all(state['development']['steps'][s]=='pending' for s in STEPS[1:])); self.assertEqual(len(state['development']['audit']),1)
 def test_legacy_posterior_initialization_is_unsafe(self):
  path=self.r/'.grill/work-items/wx/state.json'; path.write_text('{}'); before=path.read_bytes()
  p=run('checkpoint',self.r,'--work-id','wx','--step','plan','--state','in-progress','--initialize-legacy','--from-step','plan','--evidence','e','--reason','explicit-decision')
  self.assertEqual((p.returncode,json.loads(p.stdout)['code']),(2,'LEGACY-INITIALIZATION-UNSAFE')); self.assertEqual(before,path.read_bytes())
 def test_state_symlink_is_blocked_without_external_read(self):
  state=self.r/'.grill/work-items/wx/state.json'; outside=Path(self.t.name)/'external-state'; outside.write_text('TOP-SECRET'); state.unlink(); state.symlink_to(outside)
  p=self.call('specify','in-progress'); self.assertEqual(p.returncode,2); self.assertNotIn('TOP-SECRET',p.stdout); self.assertEqual(outside.read_text(),'TOP-SECRET')
if __name__=='__main__': unittest.main()
