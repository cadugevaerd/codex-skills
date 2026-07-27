---
name: backlog-import
description: Migra um JSON completo do Backlog v1 para v2 somente após proposta e confirmação explícita.
argument-hint: "LEGACY_JSON_PATH --db PATH --backlogctl PATH"
user-invocable: true
disable-model-invocation: true
---
# Migração agent-led V1 JSON → V2

Esta skill é um workflow do agente, não um comando `backlogctl import`/`migrate`. Ela nunca edita, move ou apaga o JSON legado e nunca acessa SQLite diretamente. Use somente o executável `<BACKLOGCTL>` exato emitido pelo bootstrap/recovery, não dependa de PATH.

## Fase 1 — proposta sem mutação

Dado o caminho completo do JSON v1:

1. Leia o arquivo inteiro e valide que é JSON válido, objeto esperado e que todos os registros são percorríveis. Preserve cada descrição legada completa, sem truncar, resumir ou confundir com `title`.
2. Antes de qualquer operação V2, execute `<BACKLOGCTL> --json doctor --db PATH`; se doctor falhar, pare e reporte stderr/exit code.
3. Produza uma proposta humana estruturada, sem executar mutações, contendo: backlogs, bindings, todos os itens, `legacy_id`, título, descrição completa, repo, status, prioridade, position, datas, mapeamentos pretendidos e lista explícita de ambiguidades. A descrição deve aparecer no texto da proposta, inclusive quando vazia.
4. Mapeie prioridades `critica|alta|media|baixa` para `critical|high|medium|low`. Mapeie estados diretamente somente `aberto→open`, `em-andamento→in_progress`, `resolvido→done`, `descartado→cancelled`, `mesclado→merged`. `promovido` nunca é mapeado silenciosamente.
5. Marque como ambiguidades bloqueantes: enum/status desconhecido; prioridade desconhecida; duplicata `(repo,id)`; data inválida; rank/position inválido; repo ou título ausente; e qualquer `promovido`. Também reporte registros incompletos ou campos não suportados.

A proposta deve declarar que o v2 não possui campo nativo de legacy-ID e que será emitido um relatório de mapa `legacy_id → v2_id`, não uma alegação de persistência desse campo. Não escreva nada até o humano confirmar explicitamente a proposta e resolver ou confirmar cada ambiguidade.

## Fase 2 — validação descartável e execução no alvo

Após confirmação humana inequívoca, defina `VALIDATION_DB` como uma nova DB descartável. Execute nela primeiro o plano confirmado completo, sempre com `<BACKLOGCTL> --json`: `store init`, `doctor`, criação e binding de cada backlog, e cada `item add` com `code`, `title`, `description`, `status`, `criticality`, `category` e `due-at` completos, seguido dos `item move` necessários. Valide todos os envelopes e movimentos; descarte `VALIDATION_DB` depois. Ela serve apenas para validar o plano e nunca é estado-alvo.

Somente se a validação passar, revalide o fingerprint do JSON legado e defina `TARGET_DB` como a DB real. Execute exatamente o mesmo plano confirmado em `TARGET_DB`, usando `<BACKLOGCTL> --json` e os mesmos campos completos. Para cada `item add` no alvo, valide estritamente antes de prosseguir: envelope `ok` verdadeiro, `operation` igual a `item add`, `contract_version` igual a `2`, `changed` verdadeiro, `warnings` vazio, `next_action` vazio e `data` exato para o mapeamento de ID e `status`, `description`, `category`, `criticality` e `due_at` (incluindo `title` e código do backlog quando expostos). Pare no primeiro mismatch.

Registre e checkpoint o mapa incremental `legacy_id → v2_id` imediatamente após cada mutação bem-sucedida no `TARGET_DB`. Em qualquer falha, atualize e checkpoint o relatório com comando, stderr, exit code e IDs já criados antes de parar. A migração cross-item não é atômica e não há rollback ou atomicidade entre itens; permita retomada pelo relatório sem duplicar mutações confirmadas.

No postflight, resolva cada registro legado por meio do mapa `legacy_id → v2_id` antes de comparar campos V2; nunca compare IDs V1 e V2 brutos como se fossem iguais. Compare cada registro individualmente, não apenas totais. Nunca use `item reconcile-status` para contornar erro de migração, nem SQL, importação nativa, mutação do arquivo legado ou acesso direto ao SQLite.
