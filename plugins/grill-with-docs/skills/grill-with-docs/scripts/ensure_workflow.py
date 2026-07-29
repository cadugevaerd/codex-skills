#!/usr/bin/env python3
"""Safe, dependency-free workflow bootstrap and read-only hook."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
VERSION='v1'; MARKER='grill-with-docs-workflow:v1'; HERE=Path(__file__).resolve(); TEMPLATE=HERE.parents[1]/'assets'/'WORKFLOW.template.md'
ESSENTIAL=('## Loop externo','## Ciclo externo de execução','specify','plan','checklist','tasks','analyze','agent-assign','agent-execute','converge','verify','review','ship','PLAN_ONLY_STOP','Spec Kit >=0.11.2','A–E','no PR')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git_root(p):
 try: return Path(subprocess.check_output(['git','-C',str(p),'rev-parse','--show-toplevel'],stderr=subprocess.DEVNULL,text=True).strip()).resolve()
 except (OSError,subprocess.CalledProcessError): return None
def compat(s): return bool(s.strip()) and all(x in s for x in ESSENTIAL)
def managed(s): return re.search(r'grill-with-docs-workflow:(v\d+)',s)
def emit(status,p=None,**kw):
 d={'status':status,**kw}
 if p: d.update(path=str(p),sha256=sha(p),version=VERSION)
 print(json.dumps(d,ensure_ascii=False,sort_keys=True))
def atomic(target,content):
 fd,n=tempfile.mkstemp(prefix='.'+target.name+'.',dir=target.parent); tmp=Path(n)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f: f.write(content); f.flush(); os.fsync(f.fileno())
  try: os.link(tmp,target); made=True
  except FileExistsError: made=False
  try:
   flags=getattr(os,'O_DIRECTORY',0); d=os.open(target.parent,os.O_RDONLY|flags); os.fsync(d); os.close(d)
  except OSError: pass
  return made
 finally:
  try: tmp.unlink()
  except FileNotFoundError: pass
def ensure(arg):
 root_arg=Path(arg).expanduser()
 if not root_arg.is_dir(): emit('BLOCKED',reason='ROOT must be existing Git top-level'); return 2
 root=root_arg.resolve()
 if git_root(root)!=root: emit('BLOCKED',reason='ROOT must be existing Git top-level'); return 2
 target=root/'WORKFLOW.md'
 try:
  if target.is_symlink() or target.resolve().parent!=root: emit('BLOCKED',reason='unsafe target'); return 2
  if target.exists():
   s=target.read_text(encoding='utf-8'); m=managed(s)
   if m and m.group(1)!=VERSION: emit('BLOCKED',target,reason='managed version mismatch'); return 2
   if (m and compat(s)) or (not m and compat(s)): emit('REUSED',target); return 0
   emit('BLOCKED',target,reason='incompatible workflow'); return 2
  made=atomic(target,TEMPLATE.read_text(encoding='utf-8'))
  if target.is_symlink() or target.resolve().parent!=root: emit('BLOCKED',reason='unsafe target after create'); return 2
  s=target.read_text(encoding='utf-8')
  if not compat(s): emit('BLOCKED',target,reason='read-back validation failed'); return 2
  emit('CREATED' if made else 'REUSED',target); return 0
 except (OSError,UnicodeError) as e: emit('BLOCKED',reason=str(e)); return 2
def hook():
 try: p=json.load(sys.stdin)
 except (json.JSONDecodeError,TypeError): print(json.dumps({'status':'BLOCKED','reason':'invalid-json'})); return 0
 if not isinstance(p,dict): print(json.dumps({'status':'BLOCKED','reason':'invalid-payload'})); return 0
 ev=p.get('hook_event_name')
 if ev not in ('SessionStart','SubagentStart'): print(json.dumps({'status':'IGNORED'})); return 0
 root=git_root(Path(p.get('cwd') or os.getcwd()))
 if root is None: print(json.dumps({'status':'BLOCKED','reason':'invalid-root'})); return 0
 path=root/'WORKFLOW.md'; msg=''
 if path.is_symlink() or (path.exists() and path.resolve().parent!=root): msg=f'WORKFLOW.md inseguro em {path}; invoque grill-with-docs para auditar.'
 elif not path.is_file(): msg=f'WORKFLOW.md ausente em {root}; invoque grill-with-docs para preparar o workflow.'
 else:
  try: s=path.read_text(encoding='utf-8')
  except OSError: s=''
  if compat(s): msg=f'Leia {path}; sha256={sha(path)}. Fluxo COMPLETO: ROADMAP/handoff → specify → plan → checklist → tasks → analyze → agent-assign → agent-execute → converge → verify → review → ship (A–E), sem PR.'
  else: msg=f'WORKFLOW.md incompatível em {path}; invoque grill-with-docs para auditar.'
 print(json.dumps({'status':'OK','hookSpecificOutput':{'hookEventName':ev,'additionalContext':msg}},ensure_ascii=False,sort_keys=True)); return 0
def main():
 a=argparse.ArgumentParser(); g=a.add_mutually_exclusive_group(required=True); g.add_argument('--ensure'); g.add_argument('--hook',action='store_true'); x=a.parse_args(); return hook() if x.hook else ensure(x.ensure)
if __name__=='__main__': raise SystemExit(main())
