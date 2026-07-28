# Migração agent-led V1 JSON → V2

## Limites e segurança

Este é o workflow agent-led específico para **JSON v1**, que o import nativo v3 não aceita. O agente lê o legado completo, mas nunca o modifica, move ou apaga e nunca manipula SQLite. O resultado deve conter um relatório `legacy_id → v2_id`, sem alegar que o legacy-ID foi persistido no banco.

Use o caminho exato `<BACKLOGCTL>` emitido pelo bootstrap/recovery, nunca dependa de PATH. Antes de qualquer operação V2, rode `<BACKLOGCTL> --json doctor --db PATH` e pare se falhar.

## Proposta obrigatória

Leia e valide o arquivo inteiro e produza, sem mutação, uma proposta estruturada com backlogs, bindings, todos os itens, IDs legados, repo, título, **descrição legada completa**, status, prioridade, posição, datas, mapeamentos e ambiguidades. Mostre a descrição integral na proposta, inclusive quando vazia; não a resuma nem a trate como título. A proposta deve bloquear escrita até confirmação humana explícita e resolução/confirmação de cada ambiguidade. Liste explicitamente: enum/status desconhecido, prioridade desconhecida, duplicata `(repo,id)`, datas inválidas, rank/position inválido, repo/título ausente e qualquer V1 `promovido`. `promovido` não pode ser mapeado silenciosamente.

Prioridades: `critica|alta|media|baixa` → `critical|high|medium|low`. Estados diretos válidos: `aberto→open`, `em-andamento→in_progress`, `resolvido→done`, `descartado→cancelled`, `mesclado→merged`.

## Validação descartável e execução confirmada

Somente após confirmação, crie `VALIDATION_DB` como nova DB descartável e execute nela o plano confirmado completo com `<BACKLOGCTL> --json`: `store init`, `doctor`, `backlog create`, `backlog bind`, cada `item add` com `code`, `title`, `description`, `status`, `criticality`, `category` e `due-at` completos, e os `item move` necessários. Valide o plano e descarte essa DB; ela nunca é estado-alvo.

Somente após a validação passar, revalide o fingerprint do JSON legado, defina `TARGET_DB` como a DB real e execute exatamente o mesmo plano com `<BACKLOGCTL> --json`. Para cada `item add` no alvo, valide estritamente o envelope: `ok` verdadeiro, `operation` `item add`, `contract_version` `2`, `changed` verdadeiro, `warnings` vazio, `next_action` vazio e `data` exato para ID mapping, status, description, category, criticality e due_at, além de title e código do backlog quando expostos. Pare no primeiro mismatch.

Escreva/checkpoint o mapa incremental `legacy_id → v2_id` imediatamente após cada mutação bem-sucedida no alvo. Em falha, atualize/checkpoint o relatório com comando, stderr, exit code e IDs já criados antes de parar. A migração cross-item não é globalmente atômica: não prometa rollback nem atomicidade entre itens; permita retomada pelo relatório.

No postflight, resolva cada registro legado por meio do mapa antes de comparar campos V2; nunca compare IDs V1 e V2 brutos como se fossem iguais. Compare cada registro individualmente, não apenas totais. Não use `item reconcile-status` para contornar erro de migração. Retenha as restrições: sem SQL, sem enviar JSON v1 ao import nativo, sem mutação do arquivo legado e sem acesso direto ao SQLite.
