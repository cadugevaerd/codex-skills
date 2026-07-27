---
name: backlog-add
description: Adiciona item a backlog existente.
argument-hint: "--db PATH --code CODE --title TITLE [--description TEXT] [--category CATEGORY] [--criticality CRITICALITY]"
user-invocable: true
disable-model-invocation: false
---
# Adicionar item

Após doctor e confirmação, execute `backlogctl [--json] item add --db PATH --code CODE --title TITLE` com as flags suportadas, incluindo `--description TEXT`, `--category`, `--criticality` e `--due-at`. `title` é o resumo; `description` é a descrição executável completa. Preserve a identidade retornada; não edite banco. Criticality válida: critical/high/medium/low.

## Contract v2.0.2
`item add --status STATE` is an initial snapshot (omitted means `open`), not a transition. Flags are command-scoped; invalid flags for this subcommand fail exit 2. Validate the returned JSON envelope immediately, including status, description, category, and criticality.
