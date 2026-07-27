---
name: backlog-archive
description: Soft-archive obsolete or source-less backlog items with an audit reason.
user-invocable: true
disable-model-invocation: true
---
# Audited item archival
After human confirmation, run `<BACKLOGCTL> --json item archive --id ID --reason TEXT --confirm --db PATH`, using the exact executable path emitted by bootstrap/recovery. This is soft archival, never deletion. Default list/export omit archived records; `show` and `list --all` preserve them for audit. Never access SQLite directly.
