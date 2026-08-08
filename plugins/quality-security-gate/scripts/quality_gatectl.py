#!/usr/bin/env python3
"""Deterministic, local, fail-closed quality/security gate."""
import argparse, hashlib, json, os, subprocess, sys, tempfile, time
from pathlib import Path

GO, NOGO, BLOCKED, USAGE = 0, 1, 2, 3
INSTRUCTIONS = ("AGENTS.md", "CLAUDE.md", ".agents/AGENTS.md", ".claude/CLAUDE.md")
MODULES = [
("MOD-001", "Governança do repo", "repository governance"), ("MOD-002", "Proteção de integração", "branch protection"),
("MOD-003", "Qualidade de código", "format/lint/build/test"), ("MOD-004", "Segredos e credenciais", "secret controls"),
("MOD-005", "SAST e políticas", "SAST"), ("MOD-006", "Dependências e licença", "dependency controls"),
("MOD-007", "CI/CD endurecido", "hardened CI"), ("MOD-008", "Artefatos e releases", "release integrity"),
("MOD-009", "IaC e container", "IaC/container"), ("MOD-010", "Aplicação/API", "application/API"),
("MOD-011", "Observabilidade e resposta", "observability"), ("MOD-012", "Auditoria e melhoria contínua", "continuous improvement")]

def digest(b): return hashlib.sha256(b).hexdigest()
def out(obj, code): print(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))); return code
def git_root(p):
    try: return Path(subprocess.check_output(["git", "-C", str(p), "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL, text=True).strip()).resolve()
    except Exception: return None
def safe_root(raw):
    p=Path(raw).expanduser()
    if not p.is_absolute() or "\x00" in str(p): raise ValueError("root must be absolute and NUL-free")
    r=git_root(p)
    if not r or not r.is_dir(): raise RuntimeError("Git root not found")
    return r
def read_instructions(root):
    result=[]; blocked=False
    for rel in INSTRUCTIONS:
        p=root/rel; item={"path":rel}
        try:
            if not p.exists(): item["status"]="absent"
            elif p.is_symlink() or not p.is_file(): item["status"]="unreadable"; blocked=True
            else:
                before=p.stat(); data=p.read_bytes(); after=p.stat()
                if before.st_mtime_ns!=after.st_mtime_ns or before.st_size!=after.st_size: item["status"]="changed_during_read"; blocked=True
                else:
                    data.decode("utf-8"); item.update(status="present", sha256=digest(data), size=len(data))
        except UnicodeDecodeError: item["status"]="unreadable"; blocked=True
        except OSError: item["status"]="unreadable"; blocked=True
        result.append(item)
    return result, blocked
def repo_fp(root):
    h=hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs[:]=sorted(d for d in dirs if d not in {".git",".quality-gate","__pycache__"} and not (Path(base)/d).is_symlink())
        for f in sorted(files):
            p=Path(base)/f
            if p.is_symlink(): continue
            try: h.update(str(p.relative_to(root)).encode()); h.update(p.read_bytes())
            except OSError: pass
    return h.hexdigest()
def level(root, instructions):
    names=[]; factors=[]; lvl=1
    allnames={p.name.lower() for p in root.rglob("*") if p.is_file() and not p.is_symlink()}
    if any(x in allnames for x in ("dockerfile","terraform.tf","main.tf")) or any("workflow" in str(x).lower() for x in root.rglob(".github/workflows/*")): lvl=max(lvl,2); factors.append("CI/container/IaC evidence")
    instruction_text=[]
    for item in instructions:
        if item.get("status") == "present":
            try:
                instruction_text.append((root / item["path"]).read_text(encoding="utf-8"))
            except OSError:
                pass
    text=" ".join(instruction_text).lower()
    if any(k in text for k in ("production","personal data","payment","public api","iam")):
        lvl=3; factors.append("explicit sensitive/production instruction")
    if any(x.name in {"openapi.yaml","openapi.yml"} or x.name.endswith(("requirements.txt","package.json")) for x in root.rglob("*")): lvl=max(lvl,2); factors.append("application/dependency evidence")
    return f"P{lvl}", factors
def modules(root):
    result=[]
    for mid,name,criterion in MODULES:
        evidence=[]
        for pat in ("SECURITY.md",".github/workflows","pyproject.toml","package-lock.json","requirements.txt","Dockerfile","terraform.tf","openapi.yaml"):
            if any(root.glob(pat)) or any(root.rglob(pat)):
                evidence.append(pat)
        result.append({"id":mid,"name":name,"status":"pending","next_action":f"Collect and validate {criterion} evidence","evidence":evidence or ["absence of evidence"]})
    return result
def write_atomic(p,data):
    p.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=".tmp-");
    with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(data,f,sort_keys=True,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,p)
def analyze(root, init):
    ins, blocked=read_instructions(root); q=root/".quality-gate"; statep=q/"state.json"
    if blocked: return {"verdict":"BLOCKED","reason":"instruction path is unsafe or changed during read","instructions":ins}, BLOCKED
    computed,factors=level(root,ins); old=None
    if statep.exists():
        try: old=json.loads(statep.read_text(encoding="utf-8"))
        except Exception: return {"verdict":"USAGE/INTEGRITY","reason":"malformed state"},USAGE
    rank=lambda x:int(x[1:])
    previous_computed=old.get("risk",{}).get("computed_level") if old else None
    previous_floor=old.get("risk",{}).get("accepted_floor") if old else None
    floor=max((previous_floor or computed), computed)
    eff=max(floor,computed)
    increase=bool(previous_computed and rank(computed)>rank(previous_computed))
    fp=repo_fp(root); stale=False
    if old: stale=(old.get("project",{}).get("repo_fingerprint")!=fp or old.get("instructions")!=ins)
    reasons=[]
    if increase: reasons.append("computed risk level increased")
    if stale: reasons.append("observed repository or instructions changed")
    if not old and not init: reasons.append("initial analysis required")
    verdict="NO-GO"
    now=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()); aid="ANL-"+digest((fp+now).encode())[:12]
    state={"schema_version":1,"project":{"root":str(root),"repo_fingerprint":fp,"observed_at":now},"risk":{"computed_level":computed,"accepted_floor":floor,"effective_level":eff,"factors":factors,"risk_increase":increase},"instructions":ins,"analysis":{"id":aid,"input_fingerprint":digest((fp+json.dumps(ins,sort_keys=True)).encode()),"status":"current","reasons":reasons},"modules":modules(root),"verdict":verdict,"next_action":"MOD-001"}
    write_atomic(statep,state); (q/"snapshots").mkdir(parents=True,exist_ok=True); write_atomic(q/"snapshots"/(aid+".json"),state)
    with (q/"events.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps({"event":"analysis","id":aid,"at":now,"verdict":verdict},sort_keys=True)+"\n")
    return state, NOGO
def status(root):
    p=root/".quality-gate/state.json"
    if not p.exists(): return {"verdict":"NO-GO","analysis":"absent","next_action":"quality-gatectl analyze --root ROOT --init"},NOGO
    try: s=json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {"verdict":"USAGE/INTEGRITY","reason":"malformed state"},USAGE
    ins,blocked=read_instructions(root); stale=blocked or s.get("instructions")!=ins or s.get("project",{}).get("repo_fingerprint")!=repo_fp(root)
    s={"verdict":"NO-GO" if stale else s.get("verdict","NO-GO"),"stale":stale,"risk":s.get("risk"),"analysis":s.get("analysis"),"modules":s.get("modules"),"next_action":s.get("next_action")}
    return s,NOGO if stale or s["verdict"]!="GO" else GO
def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("analyze"); a.add_argument("--root",required=True); a.add_argument("--init",action="store_true"); a.add_argument("--json",action="store_true")
    s=sub.add_parser("status"); s.add_argument("--root",required=True); s.add_argument("--json",action="store_true")
    try:
        x=ap.parse_args(); root=safe_root(x.root); result,code=analyze(root,x.init) if x.cmd=="analyze" else status(root); return out(result,code)
    except (ValueError,RuntimeError) as e: return out({"verdict":"USAGE/INTEGRITY","reason":str(e)},USAGE)
    except Exception as e: return out({"verdict":"BLOCKED","reason":str(e)},BLOCKED)
if __name__=="__main__": sys.exit(main())
