---
name: backlog-list
description: Lista backlogs ou itens sem mutação.
argument-hint: "--db PATH [--code CODE]"
user-invocable: true
disable-model-invocation: false
---
# Listar

Preserve estados, IDs e ordene por `criticality` e depois por `position`. JSON sempre inclui `description` em cada item, inclusive como string vazia. O bootstrap é automático no Claude Code; no Codex, use o verificador manual quando necessário.

## Contract CLI v2.3.0
Flags are command-scoped. Archived items are omitted by default; use `list --all` for audit. Do not assume a globally documented flag applies to this subcommand.
