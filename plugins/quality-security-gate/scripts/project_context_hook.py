#!/usr/bin/env python3
import json, os, subprocess, sys
from pathlib import Path

def main():
    try: payload=json.load(sys.stdin); cwd=payload.get("cwd") or os.getcwd()
    except Exception: payload={}; cwd=os.getcwd()
    try: root=Path(subprocess.check_output(["git","-C",cwd,"rev-parse","--show-toplevel"],stderr=subprocess.DEVNULL,text=True).strip()).resolve()
    except Exception: root=Path(cwd).resolve()
    state=root/".quality-gate/state.json"; level="unknown"; analysis="absent"; next_step="run analyze --init"
    if state.exists():
        try:
            s=json.loads(state.read_text(encoding="utf-8")); level=s.get("risk",{}).get("effective_level","unknown"); analysis=s.get("analysis",{}).get("status","current"); next_step=s.get("next_action") or "review status"
        except Exception: analysis="invalid"; next_step="repair state with analyze"
    msg=f"root={root}; level={level}; analysis={analysis}; next={next_step}"
    print(json.dumps({"hookSpecificOutput":{"additionalContext":msg}},separators=(",",":")))
if __name__=="__main__": main()
