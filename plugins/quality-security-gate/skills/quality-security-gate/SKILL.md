---
name: quality-security-gate
description: Orchestrates local quality/security gate analysis and status.
---

# Quality Security Gate

Use the bundled `scripts/quality_gatectl.py` to run `analyze --root PATH --init` and
read-only `status --root PATH --json`. Only `analyze` is allowed to mutate `.quality-gate/`
(state, snapshots, and event log); `status` and the context hook must not write files.
Explain evidence and gaps; never conclude a module complete. This skill is an orchestrator
only: it must not alter workflows, configuration, branch protections, secrets, or code; run
remote scans/DAST; or claim compliance from file presence alone. Ask for explicit human
approval before any future mutation outside the CLI contract.
