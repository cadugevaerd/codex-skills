---
name: grill-with-docs
description: Entrevista decisões arquiteturais uma por vez, converge por fronteira auditável e mantém ROADMAP por fases.
argument-hint: "iniciar|retomar|pausar|auditar <diretório>"
---
# Grill with Docs

Este é um protocolo de entrevista e preparação **plan-only**. Ele transforma decisões de arquitetura em artefatos rastreáveis e para antes da execução externa.

## Contrato de entradas

A sessão tem exatamente estas oito entradas, nesta lista normativa:

1. `.specify/memory/constitution.md`
2. `WORKFLOW.md`
3. `CONTEXT.md`
4. `docs/adr/`
5. `ROADMAP.md`
6. `DECISION-BACKLOG.md`
7. `PLAN-CONTEXT.md`
8. `handoffs/FASE-NNN-SPECIFY-HANDOFF.md` selecionado

Não chame outros artefatos de entrada. Os auxiliares de sessão são separados e não contam como entradas: `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl`, `state.json` e `AUDIT.md`.

- `CONTEXT.md` contém apenas glossário e linguagem ubíqua.
- `docs/adr/` contém decisões difíceis de reverter, surpreendentes sem contexto e com trade-offs reais.
- `ROADMAP.md` contém fases, ordem explícita de execução, dependências, estados e handoff.
- `DECISION-BACKLOG.md` contém decisões adiadas, com owner, evidência necessária e gatilho.
- `PLAN-CONTEXT.md` contém o HOW técnico cumulativo para `plan`.
- O handoff selecionado contém somente WHAT/WHY de uma fase.

## Modos e preflight

Resolva o Git root antes de qualquer leitura relativa. Em `iniciar` ou `retomar`, materialize o workflow com:

```text
python3 "${CLAUDE_PLUGIN_ROOT}/skills/grill-with-docs/scripts/ensure_workflow.py" --ensure ROOT
```

Quando `CLAUDE_PLUGIN_ROOT` não estiver disponível, use o path equivalente da skill. Exija JSON válido com resultado `CREATED` ou `REUSED`; qualquer outro resultado, erro ou ausência de `WORKFLOW.md` é `BLOCKED`. Depois, releia `WORKFLOW.md` e grave no `state.json`, antes da primeira pergunta, o path canônico e o hash do workflow.

`auditar` é estritamente read-only: nunca chama `ensure_workflow.py`. Se `WORKFLOW.md` faltar, o resultado é `NO-GO`. Hooks de runtime (`SessionStart` e `SubagentStart`) apenas injetam contexto read-only; a confiança no hook segue o Codex `/hooks`, não este protocolo.

O preflight Spec Kit exige: Spec Kit initialized; `.specify/templates/constitution-template.md` local existente; workflow lido; paths canônicos sem traversal; e os artefatos obrigatórios materializáveis. Nunca use bundle de constitution nem invente princípios. Criação ou emenda da constitution só ocorre após aprovação explícita, com SemVer, datas e governance válidos. Enfraquecimento de princípio `NON-NEGOTIABLE` exige ADR.

A materialização é incremental, idempotente e preserva os oito artefatos. Nunca sobrescreva conteúdo humano ou crie caminhos fora do Git root. Falha de preflight, schema, path, materialização ou hash é `BLOCKED` em `iniciar|retomar` e `NO-GO` em `auditar`.

## Entrevista incremental

```text
INIT → MAP_FRONTIER → ASK_ONE → RECORD → RECOMPUTE_FRONTIER
                         ↑                    │
                         └──── decisões ──────┘
                                              ↓
                 COMPLETE | BLOCKED | SAFETY_STOP | PAUSED_USER
```

1. Classifique `brownfield`, `greenfield com autoridade externa` ou `greenfield com EVIDENCE GAP`; registre fonte oficial, versão/data, seção e consulta.
2. Classifique afirmações como `official-doc`, `code`, `test`, `existing-adr`, `user-decision` ou `inference`, com estado `verified`, `partial` ou `unverified`.
3. Crie/retome os auxiliares e carregue a fronteira inteira.
4. Selecione uma DQ `open` de maior impacto com dependências satisfeitas e faça exatamente uma pergunta atômica: Evidência, Recomendação, Opções, custo de implementação/operação/reversão e pergunta.
5. Registre uma transição `resolved`, `deferred`, `split`, `blocked` ou `out-of-scope`; faça impact scan e atualize somente os artefatos afetados.
6. Acrescente uma linha JSON válida e append-only ao `ROUND-LOG.jsonl`; recalcule a fronteira inteira antes da próxima pergunta.

Mesmo fingerprint admite no máximo duas perguntas sem evidência nova. Depois, decisão não crítica vira `deferred`, crítica vira `blocked` ou a sessão entra em `SAFETY_STOP`. Uma clarificação por DQ é permitida. Duas rodadas sem progresso, três expansões consecutivas ou 25 perguntas materiais exigem checkpoint e `SAFETY_STOP`. `pausar`/`stop` grava `PAUSED_USER`. Contradições nunca são sobrescritas.

## ROADMAP e handoff

A ordem de execução vem do campo explícito `execution-order`, independentemente dos IDs `FASE-NNN`. O auditor exige DAG, predecessores completos e `active_phase` coerente no state. Um item `open` do backlog ligado à fase bloqueia a fase; somente uma fase pode estar `ready-for-specify`.

Para `GO`, a fase selecionada deve ser a primeira incompleta na ordem, estar pronta, ter dependências completas, nenhum BL aberto e handoff exclusivo consistente. O handoff entrega WHAT/WHY. `PLAN-CONTEXT.md`, ADRs e `CONTEXT.md` são consumidos por `plan` para HOW; não coloque HOW no handoff.

## Terminal `PLAN_ONLY_STOP`

Quando o pacote estiver validado, a auditoria for `GO` e o handoff selecionado for entregue, emita `PLAN_ONLY_STOP` e pare. Não chame `specify` ou `plan`, não edite código, não crie branch, commit ou merge. Agentes externos executarão o workflow depois. `specify`, quando executado externamente, recebe somente o handoff selecionado; `plan` recebe `PLAN-CONTEXT.md`, ADRs e `CONTEXT.md`.

## Auditoria e ciclo futuro

O auditor retorna exatamente: código `0 GO`, `1 NO-GO`, `2 BLOCKED`. `GO` imprime a fase selecionada e o path do handoff. `NO-GO` cobre inconsistência estrutural, workflow ausente em auditoria ou múltiplas fases ready. `BLOCKED` cobre preflight/externo não resolvido em sessão mutável.

Após ship, em ciclo futuro, marque a fase como `complete`; torne a próxima `ready` somente se dependências e BL permitirem; registre decisões, ADRs e termos no glossário. Nunca avance automaticamente nesta sessão.
