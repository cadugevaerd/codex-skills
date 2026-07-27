---
name: backlog-import
description: Migra um JSON completo do Backlog v1 para v2 somente após proposta e confirmação explícita.
argument-hint: "LEGACY_JSON_PATH --db PATH --backlogctl PATH"
user-invocable: true
disable-model-invocation: true
---
# Migração agent-led V1 JSON → V2

Esta skill é um workflow do agente, não um comando `backlogctl import`/`migrate`. Ela nunca edita, move ou apaga o JSON legado e nunca acessa SQLite diretamente. Use somente o executável `backlogctl` exato emitido pelo bootstrap (não dependa de PATH; no Codex não há hook SessionStart).

## Fase 1 — proposta sem mutação

Dado o caminho completo do JSON v1:

1. Leia o arquivo inteiro e valide que é JSON válido, objeto esperado e que todos os registros são percorríveis. Preserve cada descrição legada completa, sem truncar, resumir ou confundir com `title`.
2. Antes de qualquer operação V2, execute `<BACKLOGCTL> --json doctor --db PATH`; se doctor falhar, pare e reporte stderr/exit code.
3. Produza uma proposta humana estruturada, sem executar mutações, contendo: backlogs, bindings, todos os itens, `legacy_id`, título, descrição completa, repo, status, prioridade, position, datas, mapeamentos pretendidos e lista explícita de ambiguidades. A descrição deve aparecer no texto da proposta, inclusive quando vazia.
4. Mapeie prioridades `critica|alta|media|baixa` para `critical|high|medium|low`. Mapeie estados diretamente somente `aberto→open`, `em-andamento→in_progress`, `resolvido→done`, `descartado→cancelled`, `mesclado→merged`. `promovido` nunca é mapeado silenciosamente.
5. Marque como ambiguidades bloqueantes: enum/status desconhecido; prioridade desconhecida; duplicata `(repo,id)`; data inválida; rank/position inválido; repo ou título ausente; e qualquer `promovido`. Também reporte registros incompletos ou campos não suportados.

A proposta deve declarar que o v2 não possui campo nativo de legacy-ID e que será emitido um relatório de mapa `legacy_id → v2_id`, não uma alegação de persistência desse campo. Não escreva nada até o humano confirmar explicitamente a proposta e resolver ou confirmar cada ambiguidade.

## Fase 2 — plano confirmado e execução

Após confirmação humana inequívoca, revalide a proposta/arquivo e execute, sempre com `--json` antes da família e `--db PATH`, somente estas chamadas públicas, usando o mesmo `<BACKLOGCTL>`:

1. `store init` (se necessário);
2. `doctor` novamente;
3. `backlog create` para cada backlog;
4. `backlog bind` para cada binding;
5. `item add --description TEXT` para cada item validado, passando a descrição completa (inclusive `""` quando a descrição confirmada estiver vazia);
6. `item transition` e/ou `item move` quando necessários para estado/posição.

Capture cada envelope de sucesso e o ID retornado. Gere ao final um relatório de migração com `legacy_id → v2_id`, backlog/binding, comandos executados, itens criados, ambiguidades confirmadas e falha/retomada. Nunca use `import`, `migrate`, SQL, edição de banco ou escrita no JSON legado.

A CLI pública tem comandos separados: a migração cross-item não é globalmente atômica. Execute o plano pré-validado em ordem, pare na primeira falha, reporte stderr/exit code e IDs já criados; permita retomar usando o relatório (sem duplicar o que já foi confirmado). Não prometa transação ou rollback automático. Erros nunca devem ser convertidos em sucesso fabricado.
