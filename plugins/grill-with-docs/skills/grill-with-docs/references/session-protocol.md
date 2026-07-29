# Protocolo de sessão

Este documento torna executáveis os gates de `iniciar|retomar|auditar` e a parada plan-only. Frases com **deve**, **nunca** e **somente** são normativas.

## Checklist de preflight

### `iniciar|retomar`

- [ ] Resolver e fixar o Git root.
- [ ] Executar `python3 "${CLAUDE_PLUGIN_ROOT}/skills/grill-with-docs/scripts/ensure_workflow.py" --ensure ROOT` (ou path equivalente da skill).
- [ ] Exigir JSON com resultado exatamente `CREATED` ou `REUSED`.
- [ ] Reler `WORKFLOW.md` e gravar seu path canônico e hash no `state.json` antes da primeira pergunta.
- [ ] Confirmar Spec Kit initialized e `.specify/templates/constitution-template.md` local.
- [ ] Confirmar as oito entradas exatas: constitution, WORKFLOW, CONTEXT, docs/adr, ROADMAP, DECISION-BACKLOG, PLAN-CONTEXT e handoff selecionado.
- [ ] Manter auxiliares separados: FRONTIER, ROUND-LOG, state e AUDIT.
- [ ] Validar paths canônicos, sem traversal, e materialização incremental/idempotente.
- [ ] Preservar artefatos existentes; não inventar princípios nem usar bundle de constitution.

Qualquer falha acima é `BLOCKED`. A constitution somente pode ser criada/emendada após aprovação, com SemVer, datas e governance; enfraquecimento `NON-NEGOTIABLE` exige ADR.

### `auditar`

- [ ] Não chamar `ensure_workflow.py`.
- [ ] Fazer somente leituras e validações.
- [ ] Se `WORKFLOW.md` faltar, retornar `NO-GO`.
- [ ] Validar ordem explícita do ROADMAP, não IDs; uma única fase `ready` e `active_phase` coerente.
- [ ] Confirmar que qualquer BL `open` ligado bloqueia a fase.
- [ ] Confirmar o handoff WHAT/WHY e a separação HOW em PLAN-CONTEXT/ADRs.

## Loop de entrevista

```text
INIT → MAP_FRONTIER → ASK_ONE → RECORD → RECOMPUTE_FRONTIER
                         ↑                    │
                         └──── decisões ──────┘
                                              ↓
                 COMPLETE | BLOCKED | SAFETY_STOP | PAUSED_USER
```

1. Classifique o cenário e registre fontes oficiais ou `EVIDENCE GAP`.
2. Carregue a FRONTIER inteira e selecione uma DQ material com dependências satisfeitas.
3. Faça exatamente uma pergunta atômica.
4. Registre evidência, resposta e uma transição: `resolved`, `deferred`, `split`, `blocked` ou `out-of-scope`.
5. Faça impact scan e atualize ADR, BL, CONTEXT, ROADMAP e dependências afetadas.
6. Acrescente uma linha válida ao ROUND-LOG append-only e recalcule a FRONTIER inteira.

Sem progresso por duas rodadas, terceira repetição do fingerprint, terceira expansão consecutiva ou 25 perguntas materiais: gravar checkpoint e `SAFETY_STOP`. Uma clarificação por DQ; depois, bloquear ou parar. `stop`/`pausar` grava `PAUSED_USER`. Contradições não são sobrescritas.

## Checklist de transição para GO

- [ ] A fase é a primeira incompleta na `execution-order` explícita.
- [ ] `active_phase` aponta para ela.
- [ ] Há somente uma fase `ready-for-specify`.
- [ ] Predecessores e dependências estão completos.
- [ ] Não há backlog `open` ligado à fase.
- [ ] Handoff exclusivo existe, é WHAT/WHY e tem referências válidas.
- [ ] PLAN-CONTEXT/ADRs/CONTEXT contêm o HOW para planejamento.
- [ ] Auditoria passou e a segunda passada não criou DQ média/alta.

O auditor retorna `0 GO`, `1 NO-GO` ou `2 BLOCKED`. `GO` imprime a fase e o handoff selecionados. `NO-GO`, `BLOCKED`, `SAFETY_STOP` e `PAUSED_USER` nunca liberam handoff.

## Parada `PLAN_ONLY_STOP`

Após pacote validado, auditoria `GO` e entrega do handoff selecionado:

1. Emitir `PLAN_ONLY_STOP`.
2. Parar imediatamente.
3. Não chamar `specify` nem `plan`.
4. Não editar código, criar branch, commit ou merge.
5. Informar que agentes externos executarão o workflow.

Se `specify` for executado fora desta sessão, recebe somente o handoff selecionado. `plan` consome PLAN-CONTEXT, ADRs e CONTEXT.

## Pós-ship em ciclo futuro

- [ ] Marcar a fase shipped como `complete`.
- [ ] Tornar a próxima fase `ready` apenas se dependências e BL permitirem.
- [ ] Registrar decisões, ADRs e novos termos no glossário.
- [ ] Reauditar antes de selecionar outro handoff.

Hooks `SessionStart`/`SubagentStart` são apenas contexto read-only; trust e configuração pertencem ao Codex `/hooks`.
