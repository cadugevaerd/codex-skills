# Compatibilidade de runtime

Compatível com o `backlogctl` real no PATH. Use `backlogctl --version` quando disponível e `backlogctl [--json] doctor --db PATH`; `--json` antecede a família e `--db` pertence a cada comando.

Implementado: `store init`, `doctor`; famílias `backlog create|list|show|edit|archive|bind`, `item add|list|show|edit|transition|move`, `context add|list|show|supersede|revoke|expire`, `format list|show|propose|apply`, `export json|markdown|consolidated`. Sucesso usa o envelope v2; falhas de domínio vão para stderr com exit 1 e uso inválido para stderr com exit 2.

Mutações de contexto devem usar `backlogctl --json context ... --db PATH` e confirmação explícita do usuário; nunca acesse SQLite diretamente. Para `format propose`, exiba a proposta e só aplique após confirmação explícita com `--confirm`.

`merge`, `import` e `update` permanecem não implementados (ou apenas disponíveis para diagnóstico). Não instalar binários placeholder ou não verificados.