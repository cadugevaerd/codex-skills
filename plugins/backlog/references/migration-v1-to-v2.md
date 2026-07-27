# Migração agent-led V1 JSON → V2

## Limites e segurança

Este é um workflow da skill `backlog-import`, não um comando `backlogctl import`/`migrate`. O agente lê o JSON v1 completo, mas nunca o modifica, move ou apaga. Nunca manipula SQLite. O `backlogctl` não tem comando nativo de import/migrate nem campo de legacy-ID; o resultado deve conter um relatório `legacy_id → v2_id`, sem alegar que esse identificador foi persistido no banco.

Use o caminho exato emitido pelo bootstrap (`--hook` no Claude Code; recuperação manual no Codex), nunca dependa de PATH. Antes de qualquer operação V2, rode `<BACKLOGCTL> --json doctor --db PATH` e pare se falhar.

## Proposta obrigatória

Leia e valide o arquivo inteiro e produza, sem mutação, uma proposta estruturada com backlogs, bindings, todos os itens, IDs legados, repo, título, **descrição legada completa**, status, prioridade, posição, datas, mapeamentos e ambiguidades. Mostre a descrição integral na proposta, inclusive quando vazia; não a resuma nem a trate como título. A proposta deve bloquear escrita até confirmação humana explícita e resolução/confirmação de cada ambiguidade. Liste explicitamente: enum/status desconhecido, prioridade desconhecida, duplicata `(repo,id)`, datas inválidas, rank/position inválido, repo/título ausente e qualquer V1 `promovido`. `promovido` não pode ser mapeado silenciosamente.

Prioridades: `critica|alta|media|baixa` → `critical|high|medium|low`. Estados diretos válidos: `aberto→open`, `em-andamento→in_progress`, `resolvido→done`, `descartado→cancelled`, `mesclado→merged`.

## Execução confirmada

Somente após confirmação, revalide em DB descartável e use `<BACKLOGCTL> --json ... --db PATH` para `store init`, `doctor`, `backlog create`, `backlog bind` e `item add --status EXPECTED --description TEXT` (sempre passando a descrição completa, incluindo `""` quando confirmada vazia). Capture o envelope retornado imediatamente para cada item e verifique status, description, category e criticality; pare na primeira divergência. Não use `item reconcile-status` para contornar erro de migração. A CLI anterior a v2.0.2 é unsupported para esta migração corrigida.

Como a CLI tem comandos separados, a migração cross-item não é globalmente atômica: execute o plano pré-validado em ordem, pare na falha, reporte stderr/exit code e IDs já criados e permita retomada a partir do relatório. Não prometa transação/rollback. Não use SQL, arquivos legados como destino, nem comandos CLI inexistentes.
No postflight, compare cada registro legado individualmente (IDs, campos, descrição, categoria, criticalidade, status e associações), não apenas totais por status. Qualquer mismatch interrompe o workflow e exige revisão humana.
