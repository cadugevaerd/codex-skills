---
name: backlog-add
description: Adiciona item a backlog existente.
argument-hint: "--db PATH --code CODE --title TITLE [--category CATEGORY] [--criticality CRITICALITY]"
user-invocable: true
disable-model-invocation: false
---
# Adicionar item

Após doctor e confirmação, execute `backlogctl [--json] item add --db PATH --code CODE --title TITLE` com flags suportadas como `--category`, `--criticality` e `--due-at`. Preserve a identidade retornada; não edite banco. Criticality válida: critical/high/medium/low.