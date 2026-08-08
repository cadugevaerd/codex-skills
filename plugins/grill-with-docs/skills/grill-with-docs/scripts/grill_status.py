#!/usr/bin/env python3
"""Read-only deterministic status projection for Grill work items."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve(); WORKSPACE=HERE.with_name('grill_workspace.py')
_spec=importlib.util.spec_from_file_location('grill_workspace_status', WORKSPACE); assert _spec and _spec.loader
_mod=importlib.util.module_from_spec(_spec); sys.modules[_spec.name]=_mod; _spec.loader.exec_module(_mod)
SEQUENCE=["specify","plan","checklist","tasks","analyze","agent-assign","agent-execute","converge","verify","review","ship"]
def git(root,*args):
 p=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,check=False); return p.stdout.strip()
def live(root):
 return {'branch':git(root,'branch','--show-current') or 'DETACHED','head':git(root,'rev-parse','--verify','HEAD'),'dirty':bool(git(root,'status','--porcelain=v1','--untracked-files=all'))}
def one(root,item):
 raw=(item/'WORK-ITEM.json').read_bytes(); meta=json.loads(raw); imm=meta.get('immutable',{}); state={}
 try: state=json.loads((item/'state.json').read_text(encoding='utf-8'))
 except (OSError,UnicodeError,json.JSONDecodeError): state={}
 dev=state.get('development') if isinstance(state,dict) else None
 tracking='legacy-untracked' if not isinstance(dev,dict) else 'tracked'
 steps=dev.get('steps',{}) if isinstance(dev,dict) else {}
 current=dev.get('current_step','unknown') if isinstance(dev,dict) else 'unknown'
 completed=[x for x in SEQUENCE if steps.get(x)=='complete'] if isinstance(steps,dict) else []
 blocked=[x for x in SEQUENCE if steps.get(x)=='blocked'] if isinstance(steps,dict) else []
 return {'identity':{'work_id':imm.get('work_id',item.name),'type':imm.get('type'),'slug':imm.get('slug'),'fingerprint':hashlib.sha256(raw).hexdigest()},'locations':{'root':str(root),'work_item':str(item)},'recorded':{'branch':imm.get('branch'),'head':imm.get('head'),'base_commit':imm.get('base_commit')},'live':live(root),'planning':{'status':state.get('status'),'milestone':state.get('milestone_status'),'active_phase':state.get('active_phase'),'modules':None,'delivery_units':None,'development_types':None},'development':{'tracking':tracking,'current':current,'completed':completed,'blocked':blocked,'steps':steps},'governance':{'constitution':imm.get('constitution'),'check_sha256':hashlib.sha256((item/'CONSTITUTION-CHECK.md').read_bytes()).hexdigest() if (item/'CONSTITUTION-CHECK.md').is_file() else None,'audit':state.get('audit_verdict'),'reconciled':(root/'.grill/global/receipts'/f"{item.name}.json").is_file()},'next_gate':blocked[0] if blocked else (SEQUENCE[len(completed)] if len(completed)<len(SEQUENCE) else 'complete'),'findings':[]}
def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('--work-id'); ap.add_argument('--current-worktree',action='store_true'); a=ap.parse_args(argv)
 root=Path(a.root).resolve(); items=[]
 if not root.is_dir(): raise SystemExit(2)
 candidates=[root/'.grill/work-items']
 if not a.current_worktree:
  common=git(root,'rev-parse','--git-common-dir')
  if common:
   out=subprocess.run(['git','-C',str(root),'worktree','list','--porcelain'],capture_output=True,text=True,check=False).stdout
   for line in out.splitlines():
    if line.startswith('worktree '): candidates.append(Path(line[9:]) / '.grill/work-items')
 seen={}
 for directory in candidates:
  if not directory.is_dir() or directory.is_symlink(): continue
  for item in sorted(directory.iterdir()):
   if not item.is_dir() or item.is_symlink() or (a.work_id and item.name!=a.work_id): continue
   value=one(directory.parent.parent,item); key=value['identity']['work_id']; fp=value['identity']['fingerprint']
   if key in seen and seen[key]['identity']['fingerprint']!=fp: value['findings']=['DUPLICATE-DIVERGENT']; value['next_gate']='BLOCKED'
   seen[key]=value
 items=sorted(seen.values(),key=lambda x:x['identity']['work_id'])
 counts={'total':len(items),'in_progress':sum(bool(x['development']['current'] not in {'unknown','complete'} and not x['development']['blocked']) for x in items),'blocked':sum(bool(x['development']['blocked'] or 'BLOCKED' in x['findings']) for x in items),'completed':sum(x['next_gate']=='complete' for x in items)}
 print(json.dumps({'schema':'grill-status/v1','summary':counts,'items':items,'next_action':'iniciar' if not items else None},ensure_ascii=False,sort_keys=True,separators=(',',':')))
 return 0
if __name__=='__main__': raise SystemExit(main())
