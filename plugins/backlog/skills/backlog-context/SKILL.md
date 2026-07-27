---
name: backlog-context
description: Executa e diagnostica a família de contextos do Backlog v2 com confirmação explícita.
argument-hint: "--db PATH"
user-invocable: true
disable-model-invocation: true
---
# Contextos

Execute primeiro `backlogctl [--json] doctor --db PATH`. A família implementada é `context add|list|show|supersede|revoke|expire`.

Para qualquer mutação, use explicitamente `backlogctl --json context ... --db PATH` e obtenha confirmação explícita do usuário antes de executar. Consultas (`list`/`show`) podem ser executadas normalmente após doctor. Nunca leia ou escreva SQLite diretamente, nem invente subcomandos ou flags.