---
name: backlog-add
description: Adiciona item a backlog existente.
argument-hint: "--db PATH --code CODE --title TITLE [--description TEXT] [--category CATEGORY] [--criticality CRITICALITY]"
user-invocable: true
disable-model-invocation: false
---
# Adicionar item

Após doctor e confirmação, execute `<BACKLOGCTL> --json item add --db PATH --code CODE --title TITLE` com as flags suportadas. Um add comum pode usar defaults; o shape completo para migração confirmada é `--code CODE --title TITLE --description TEXT [--status STATE] [--criticality CRITICALITY] [--category CATEGORY] [--due-at TIMESTAMP]`. `title` é o resumo; `description` é a descrição executável completa. Preserve a identidade retornada; não edite banco. Criticality válida: critical/high/medium/low.

## Contract CLI v2.3.0
`item add --status STATE` is an initial snapshot (omitted means `open`), not a transition. Para validar envelopes, use o caminho executável exato `<BACKLOGCTL>` e `--json`; não use apenas o nome encontrado no PATH. Flags are command-scoped; invalid flags for this subcommand fail exit 2. No plano de migração confirmado, valide imediatamente o envelope retornado, incluindo status, description, category, criticality e due_at; isso não torna todos esses flags obrigatórios em um add interativo comum.
