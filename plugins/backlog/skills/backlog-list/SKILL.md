---
name: backlog-list
description: Lista backlogs ou itens sem mutação.
argument-hint: "--db PATH [--code CODE]"
user-invocable: true
disable-model-invocation: false
---
# Listar

Preserve estados, IDs e a ordem criticality então position. JSON sempre inclui `description` em cada item, inclusive como string vazia. O bootstrap é automático no Claude Code; no Codex, use o verificador manual quando necessário.