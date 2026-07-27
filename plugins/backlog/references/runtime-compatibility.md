# Compatibilidade de runtime

Compatível somente com o `backlogctl` do release v2.0.2 ou posterior. Um CLI anterior a v2.0.2 é incompatível com este contrato corrigido e deve falhar fechado; não tente descobrir a FSM sondando o banco ou itens reais. Use o caminho exato emitido pelo hook SessionStart no Claude Code ou pela recuperação manual no Codex; nunca presuma que está no PATH.

Implementado: `store init`, `doctor`; famílias `backlog create|list|show|edit|archive|bind`, `item add|list|show|edit|transition|move|reconcile-status|archive`, `context add|list|show|supersede|revoke|expire`, `format list|show|propose|apply`, `export json|markdown|consolidated`. Flags são específicas do comando; flag conhecida mas inválida para a subcommand resulta em exit 2. `item add --status` é snapshot inicial; `item transition --status` é a transição normal (`--to` não existe). Sucesso usa o envelope v2; falhas de domínio vão para stderr com exit 1 e uso inválido para stderr com exit 2.

Mutações de contexto devem usar `backlogctl --json context ... --db PATH` e confirmação explícita do usuário; nunca acesse SQLite diretamente. Para `format propose`, exiba a proposta e só aplique após confirmação explícita com `--confirm`.

O runtime compatível é o `backlogctl` do release v2.0.2 ou posterior, instalado/reutilizado pelo bootstrap e validado com SHA-256. No Claude Code o hook SessionStart fornece o caminho exato; no Codex, use a recuperação manual quando necessário. Nunca instale binários não verificados.

`reconcile-status` e `archive` são operações administrativas auditadas e exigem `--reason` e `--confirm`; não substituem migração. Arquivados ficam fora de list/export por padrão e aparecem em show/list --all. Migrações devem usar DB descartável para validar o plano, confirmar cada item e parar no primeiro mismatch.