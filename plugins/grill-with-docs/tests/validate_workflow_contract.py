#!/usr/bin/env python3
"""Focused contract tests (stdlib only). RED baseline: old implementation fails template/hook/bootstrap cases."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE=Path(__file__).resolve(); PLUGIN=HERE.parents[1]; SCRIPT=PLUGIN/'skills/grill-with-docs/scripts/ensure_workflow.py'; WS=PLUGIN/'skills/grill-with-docs/scripts/grill_workspace.py'; TEMPLATE=PLUGIN/'skills/grill-with-docs/assets/WORKFLOW.template.md'; HOOKS=PLUGIN/'hooks/hooks.json'; MARK='grill-with-docs-workflow:v2'

def symlink_supported():
 with tempfile.TemporaryDirectory() as temporary:
  root=Path(temporary); target=root/'target'; target.mkdir()
  try: (root/'link').symlink_to(target,target_is_directory=True)
  except (OSError,NotImplementedError): return False
  return True

SYMLINK_SUPPORTED=symlink_supported()

def run(*args,cwd=None,input=None): return subprocess.run([sys.executable,str(SCRIPT),*args],cwd=cwd,input=input,text=True,capture_output=True)
def snapshot(root):
 out={}
 for path in sorted(root.rglob('*')):
  rel=path.relative_to(root).as_posix()
  if rel == '.git' or rel.startswith('.git/'):
   continue
  st=path.lstat(); out[rel]=('link',os.readlink(path),st.st_mtime_ns) if path.is_symlink() else (('file',path.read_bytes(),st.st_mtime_ns) if path.is_file() else ('dir',st.st_mtime_ns))
 return out
class Contract(unittest.TestCase):
 def setUp(self): self.t=tempfile.TemporaryDirectory(); self.root=Path(self.t.name); subprocess.run(['git','init','-q'],cwd=self.root,check=True)
 def tearDown(self): self.t.cleanup()
 def test_template_contract(self):
  s=TEMPLATE.read_text(); self.assertIn(MARK,s)
  ordered=['specify','plan','checklist','tasks','analyze','agent-assign','agent-execute','converge','verify','review','ship']
  cycle=s.split('## Ciclo externo de execução (11 etapas)',1)[1]
  positions=[cycle.index(x) for x in ordered]; self.assertEqual(positions,sorted(positions))
  self.assertLess(s.index('antes de `specify`'),s.index('## Ciclo externo de execução'))
  self.assertTrue(all(x in s for x in ordered+['PLAN_ONLY_STOP','Spec Kit >=0.11.2','cleanup warnings','A-E','no PR']))
 def test_create_reuse_hash_readback(self):
  r=run('--ensure',str(self.root)); self.assertEqual(r.returncode,0); o=json.loads(r.stdout); self.assertEqual(o['status'],'CREATED'); p=self.root/'WORKFLOW.md'; self.assertEqual(o['sha256'],hashlib.sha256(p.read_bytes()).hexdigest()); b=p.read_bytes(); r=run('--ensure',str(self.root)); self.assertEqual(json.loads(r.stdout)['status'],'REUSED'); self.assertEqual(b,p.read_bytes())
 def test_versions_and_humans(self):
  p=self.root/'WORKFLOW.md'; p.write_text(MARK.replace('v2','v3')); self.assertEqual(run('--ensure',str(self.root)).returncode,2)
  p.write_text(TEMPLATE.read_text().replace('<!-- grill-with-docs-workflow:v2 -->','<!-- human-maintained equivalent -->')); b=p.read_bytes(); self.assertEqual(json.loads(run('--ensure',str(self.root)).stdout)['status'],'REUSED'); self.assertEqual(b,p.read_bytes())
  p.write_text('human'); self.assertEqual(run('--ensure',str(self.root)).returncode,2)
  p.write_bytes(b'\xff\xfe'); r=run('--ensure',str(self.root)); self.assertEqual(r.returncode,2); self.assertNotIn('Traceback',r.stderr)
 def test_roots_and_concurrency(self):
  self.assertEqual(run('--ensure',str(self.root/'x')).returncode,2); self.assertEqual(run('--ensure',str(self.root/'sub')).returncode,2)
  r=run('--ensure','.',cwd=self.root); self.assertEqual(r.returncode,0,r.stdout+r.stderr); (self.root/'WORKFLOW.md').unlink(); p=self.root/'WORKFLOW.md'
  import multiprocessing
  with multiprocessing.Pool(6) as pool: results=pool.starmap(run,[('--ensure',str(self.root))]*6)
  self.assertTrue(all(x.returncode==0 for x in results)); self.assertIn('grill-with-docs-workflow:v2',p.read_text())
 @unittest.skipUnless(SYMLINK_SUPPORTED,'symlink creation is unavailable')
 def test_symlink_workflow_is_rejected(self):
  self.assertEqual(run('--ensure',str(self.root)).returncode,0); p=self.root/'WORKFLOW.md'; p.unlink(); p.symlink_to(self.root/'outside'); self.assertEqual(run('--ensure',str(self.root)).returncode,2)
 def test_hook_events_context_missing_invalid(self):
  run('--ensure',str(self.root));
  for ev in ('SessionStart','SubagentStart'):
   r=run('--hook',cwd=self.root,input=json.dumps({'hook_event_name':ev,'cwd':str(self.root)})); self.assertEqual(r.returncode,0); o=json.loads(r.stdout); self.assertIn('agent-assign',o['hookSpecificOutput']['additionalContext']); self.assertIn(hashlib.sha256((self.root/'WORKFLOW.md').read_bytes()).hexdigest(),o['hookSpecificOutput']['additionalContext'])
  (self.root/'WORKFLOW.md').unlink(); r=run('--hook',cwd=self.root,input='{"hook_event_name":"SessionStart","cwd":"%s"}'%self.root); self.assertEqual(r.returncode,0); self.assertIn('ausente',r.stdout); self.assertFalse((PLUGIN/'PLUGIN_DATA').exists())
  self.assertEqual(run('--hook',cwd=self.root,input='{').returncode,0); self.assertEqual(run('--hook',cwd=self.root,input=json.dumps({'hook_event_name':'Other','cwd':str(self.root)})).returncode,0)
 def test_hook_status_malformed_is_blocked(self):
  run('--ensure',str(self.root)); payload=json.dumps({'hook_event_name':'SessionStart','cwd':str(self.root)})
  r=run('--hook',cwd=self.root,input=payload); self.assertEqual(r.returncode,0); self.assertIn('Itens:',r.stdout)
 def test_hook_stderr_is_empty_and_bounded(self):
  r=run('--hook',cwd=self.root,input='{'); self.assertEqual(r.stderr,''); self.assertLessEqual(len(r.stdout),2048)
  x=json.loads(HOOKS.read_text()); self.assertEqual(set(x['hooks']),{'SessionStart','SubagentStart'}); cmd=x['hooks']['SessionStart'][0]['hooks'][0]['command']; self.assertEqual(cmd,x['hooks']['SubagentStart'][0]['hooks'][0]['command']); self.assertIsInstance(cmd,str); self.assertNotIn('args',cmd); self.assertIn('${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}',cmd)
  run('--ensure',str(self.root)); payload=json.dumps({'hook_event_name':'SessionStart','cwd':str(self.root)})
  for variable in ('PLUGIN_ROOT','CLAUDE_PLUGIN_ROOT'):
   env=os.environ.copy(); env.pop('PLUGIN_ROOT',None); env.pop('CLAUDE_PLUGIN_ROOT',None); env[variable]=str(PLUGIN)
   result=subprocess.run(cmd,shell=True,cwd=self.root,input=payload,text=True,capture_output=True,env=env)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr); self.assertIn('agent-assign',result.stdout)
 def test_session_start_sources_are_all_supported_and_read_only(self):
  run('--ensure',str(self.root)); before=snapshot(self.root)
  for source in ('startup','resume','clear','compact','fork'):
   with self.subTest(source=source):
    r=run('--hook',cwd=self.root,input=json.dumps({'hook_event_name':'SessionStart','source':source,'cwd':str(self.root)})); self.assertEqual(r.returncode,0); self.assertEqual(r.stderr,''); payload=json.loads(r.stdout); self.assertEqual(payload['hookSpecificOutput']['hookEventName'],'SessionStart'); self.assertIn('Itens: 0',payload['hookSpecificOutput']['additionalContext']); self.assertIn('grill_workspace.py init',payload['hookSpecificOutput']['additionalContext'])
  self.assertEqual(before,snapshot(self.root))
 def test_subagent_start_is_supported_and_read_only(self):
  run('--ensure',str(self.root)); before=snapshot(self.root); r=run('--hook',cwd=self.root,input=json.dumps({'hook_event_name':'SubagentStart','cwd':str(self.root),'agent_type':'worker'})); self.assertEqual(r.returncode,0); self.assertEqual(r.stderr,''); self.assertEqual(json.loads(r.stdout)['hookSpecificOutput']['hookEventName'],'SubagentStart'); self.assertEqual(before,snapshot(self.root))
 def test_hook_one_real_item_projects_id_branch_step_and_gate(self):
  run('--ensure',str(self.root)); p=subprocess.run([sys.executable,str(WS),'init',str(self.root),'--type','feature','--slug','alpha','--work-id','wx'],text=True,capture_output=True); self.assertEqual(p.returncode,0,p.stdout+p.stderr); before=snapshot(self.root)
  r=run('--hook',cwd=self.root,input=json.dumps({'hook_event_name':'SessionStart','source':'resume','cwd':str(self.root)})); context=json.loads(r.stdout)['hookSpecificOutput']['additionalContext']; self.assertIn('id=wx',context); self.assertIn('branch=',context); self.assertIn('etapa=specify',context); self.assertIn('0/11',context); self.assertIn('próximo gate=',context); self.assertEqual(before,snapshot(self.root))
 def test_hook_many_real_items_lists_ids_and_work_id_guidance(self):
  run('--ensure',str(self.root))
  for wid in ('wx','wy'): self.assertEqual(subprocess.run([sys.executable,str(WS),'init',str(self.root),'--type','feature','--slug',wid,'--work-id',wid],capture_output=True).returncode,0)
  before=snapshot(self.root); r=run('--hook',cwd=self.root,input=json.dumps({'hook_event_name':'SessionStart','source':'compact','cwd':str(self.root)})); context=json.loads(r.stdout)['hookSpecificOutput']['additionalContext']; self.assertIn('Itens: 2',context); self.assertIn('wx:',context); self.assertIn('wy:',context); self.assertIn('--work-id',context); self.assertEqual(before,snapshot(self.root))
 @unittest.skipUnless(SYMLINK_SUPPORTED,'symlink creation is unavailable')
 def test_hook_unsafe_status_is_blocked_without_external_read(self):
  run('--ensure',str(self.root)); self.assertEqual(subprocess.run([sys.executable,str(WS),'init',str(self.root),'--type','feature','--slug','alpha','--work-id','wx'],capture_output=True).returncode,0); state=self.root/'.grill/work-items/wx/state.json'; external=Path(self.t.name)/'secret'; external.write_text('TOP-SECRET'); state.unlink(); state.symlink_to(external); before=external.read_bytes()
  r=run('--hook',cwd=self.root,input=json.dumps({'hook_event_name':'SessionStart','source':'startup','cwd':str(self.root)})); self.assertEqual(r.returncode,0); self.assertEqual(r.stderr,''); self.assertIn('BLOCKED status',r.stdout); self.assertNotIn('TOP-SECRET',r.stdout); self.assertEqual(before,external.read_bytes())
 def test_hook_long_context_is_bounded_with_marker(self):
  nested=Path(self.t.name)/Path(*(['x'*100]*14)); nested.mkdir(parents=True); subprocess.run(['git','init','-q',str(nested)],check=True); self.assertEqual(run('--ensure',str(nested)).returncode,0)
  r=run('--hook',cwd=nested,input=json.dumps({'hook_event_name':'SessionStart','source':'fork','cwd':str(nested)})); self.assertEqual(r.returncode,0); self.assertEqual(r.stderr,''); self.assertLessEqual(len(r.stdout),2048); self.assertIn('[TRUNCATED]',r.stdout); json.loads(r.stdout)
if __name__=='__main__': unittest.main()
