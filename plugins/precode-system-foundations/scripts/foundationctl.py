#!/usr/bin/env python3
"""Deterministic foundation state CLI; stdlib only."""
import argparse, copy, datetime as dt, json, os, re, tempfile, uuid
from pathlib import Path

STATUSES={"existing","missing","invalid","not-verifiable","necessary"}; CONF={"verified","inferred","unknown"}
def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)
def atomic(p, data):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=f".{p.name}.",dir=p.parent); os.close(fd)
    try:
        with open(tmp,"w",encoding="utf-8") as f: json.dump(data,f,indent=2,ensure_ascii=False); f.write("\n"); os.replace(tmp,p)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def validate(d):
    errs=[]
    if not isinstance(d,dict) or d.get("schema_version")!="1.1.0": errs.append("schema_version must be 1.1.0")
    for k in ("project","modules","recommendations","open_questions","change_log"):
        if k not in d: errs.append(f"missing top-level field: {k}")
    ids=[]; mods=d.get("modules",[])
    if not isinstance(mods,list): errs.append("modules must be an array"); mods=[]
    for m in mods:
        if not isinstance(m,dict): errs.append("module must be object"); continue
        mid=m.get("id")
        if not isinstance(mid,str) or not re.fullmatch(r"MOD-[0-9]{3,}",mid): errs.append(f"invalid module id: {mid}")
        if mid in ids: errs.append(f"duplicate module id: {mid}")
        ids.append(mid)
        if m.get("status") not in STATUSES: errs.append(f"invalid status for {mid}")
        if m.get("confidence") not in CONF: errs.append(f"invalid confidence for {mid}")
        if not isinstance(m.get("evidence"),list): errs.append(f"evidence must be array for {mid}")
    r=d.get("recommendations",{})
    if not isinstance(r,dict) or r.get("decision_status") not in {"proposed","approved","blocked"}: errs.append("invalid recommendation decision_status")
    refs=set(ids)
    if isinstance(r,dict):
        for phase in ("mvp","go_live","future"):
            for x in r.get(phase,[]):
                if x not in refs: errs.append(f"recommendation {x} is not a module")
    return errs
def pointer_parts(path):
    if not path.startswith("/"): raise ValueError("JSON Pointer must start with /")
    return [x.replace("~1","/").replace("~0","~") for x in path[1:].split("/") if x!=""]
def resolve(doc, parts):
    cur=doc
    for p in parts: cur=cur[int(p)] if isinstance(cur,list) else cur[p]
    return cur
def patch_one(doc, op):
    typ,path=op.get("op"),op.get("path"); parts=pointer_parts(path)
    if typ=="test":
        if resolve(doc,parts)!=op.get("value"): raise ValueError(f"test failed at {path}")
        return
    if typ not in {"add","remove","replace"}: raise ValueError("only add/remove/replace/test supported")
    if not parts: raise ValueError("root patch is not supported")
    parent=resolve(doc,parts[:-1]); key=parts[-1]
    if isinstance(parent,list):
        i=len(parent) if key=="-" else int(key)
        if typ=="add": parent.insert(i,copy.deepcopy(op["value"]))
        elif typ=="remove": parent.pop(i)
        else: parent[i]=copy.deepcopy(op["value"])
    else:
        if typ=="remove": del parent[key]
        elif typ=="replace" and key not in parent: raise ValueError(f"missing path {path}")
        else: parent[key]=copy.deepcopy(op["value"])
def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    i=sub.add_parser("init"); i.add_argument("path"); i.add_argument("--project",default="Example")
    v=sub.add_parser("validate"); v.add_argument("path")
    q=sub.add_parser("apply-patch"); q.add_argument("path"); q.add_argument("patch")
    a=ap.parse_args()
    try:
        if a.cmd=="init":
            d=load(Path(__file__).parents[1]/"templates/foundation.json"); d["project"]["name"]=a.project; d["project"]["root"]=str(Path(a.path).parent); atomic(a.path,d); print(json.dumps({"ok":True,"path":a.path}))
        elif a.cmd=="validate":
            e=validate(load(a.path)); print(json.dumps({"valid":not e,"errors":e},ensure_ascii=False)); return 0 if not e else 1
        else:
            d=load(a.path); ops=load(a.patch)
            if not isinstance(ops,list): raise ValueError("patch must be an array")
            trial=copy.deepcopy(d)
            for op in ops: patch_one(trial,op)
            errors=validate(trial)
            if errors: raise ValueError("semantic validation failed: "+"; ".join(errors))
            now=dt.datetime.now(dt.timezone.utc).isoformat(); existing={x.get("id") for x in d.get("change_log",[])}
            for n,op in enumerate(ops):
                cid="CHG-"+uuid.uuid4().hex[:12].upper()
                while cid in existing: cid="CHG-"+uuid.uuid4().hex[:12].upper()
                existing.add(cid); trial["change_log"].append({"id":cid,"at":now,"operation":op["op"],"path":op["path"]})
            atomic(a.path,trial); print(json.dumps({"ok":True,"applied":len(ops)}))
        return 0
    except (OSError,ValueError,KeyError,IndexError,TypeError,json.JSONDecodeError) as e: print(json.dumps({"ok":False,"error":str(e)})); return 2
if __name__=="__main__": raise SystemExit(main())
