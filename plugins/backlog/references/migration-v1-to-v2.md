# Migração v1 → v2

A migração documental v2 usa exclusivamente `backlogctl`; não edite JSON legado nem SQLite diretamente. Antes de qualquer operação, execute `backlogctl [--json] doctor --db PATH`.

Para dados já v2, use as operações implementadas e os exports `json`, `markdown` e `consolidated` conforme `references/contract.md`. Contextos estão disponíveis por `backlogctl --json context add|list|show|supersede|revoke|expire --db PATH`; mutações de contexto exigem confirmação explícita do usuário. A família `format` também está disponível: use `format list|show|propose|apply`; mostre a proposta/diff e só execute `format apply` após confirmação explícita, com `--confirm`.

`merge`, `import` e `update` continuam não implementados (podem ser apenas diagnosticados pelo doctor). Não os trate como operações disponíveis nem faça mutação alternativa.