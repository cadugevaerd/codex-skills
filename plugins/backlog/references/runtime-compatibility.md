# Compatibilidade de runtime

Compatível com o `backlogctl` do release v2.0.0. Use o caminho exato emitido pelo hook SessionStart no Claude Code ou pela recuperação manual no Codex; nunca presuma que está no PATH.

Implementado: `store init`, `doctor`; famílias `backlog create|list|show|edit|archive|bind`, `item add|list|show|edit|transition|move`, `context add|list|show|supersede|revoke|expire`, `format list|show|propose|apply`, `export json|markdown|consolidated`. Sucesso usa o envelope v2; falhas de domínio vão para stderr com exit 1 e uso inválido para stderr com exit 2.

Mutações de contexto devem usar `backlogctl --json context ... --db PATH` e confirmação explícita do usuário; nunca acesse SQLite diretamente. Para `format propose`, exiba a proposta e só aplique após confirmação explícita com `--confirm`.

O runtime compatível é o `backlogctl` do release v2.0.0, instalado/reutilizado pelo bootstrap e validado com SHA-256. No Claude Code o hook SessionStart fornece o caminho exato; no Codex, use a recuperação manual quando necessário. Nunca instale binários não verificados.