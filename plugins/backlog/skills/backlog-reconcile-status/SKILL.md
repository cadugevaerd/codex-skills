---
name: backlog-reconcile-status
description: Audited human-confirmed recovery of a verified backlog status inconsistency.
user-invocable: true
disable-model-invocation: true
---
# Audited status reconciliation
Use only after human confirmation and independent verification of the defect. Run `<BACKLOGCTL> --json item reconcile-status --id ID --status STATE --reason TEXT --confirm --db PATH`, using the exact executable path emitted by bootstrap/recovery. This intentionally bypasses the normal FSM; it is never a migration shortcut or normal transition. Capture the JSON envelope and audit reason. Never inspect or edit SQLite directly.
