# Protocolo de sessão

## Máquina de estados

```text
INIT → MAP_FRONTIER → ASK_ONE → RECORD → RECOMPUTE_FRONTIER
                         ↑                    │
                         └──── decisões ──────┘
                                              ↓
                 COMPLETE | BLOCKED | SAFETY_STOP | PAUSED_USER
```

1. Classifique brownfield/greenfield e modo ADR (`requested` ou `selective`).
2. Registre fontes oficiais ou `EVIDENCE GAP`.
3. Crie/retome `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl` e `state.json`.
4. Escolha uma DQ material aberta, faça uma pergunta atômica e registre resposta/evidência.
5. Antes da próxima pergunta, aplique uma transição: `resolved`, `deferred`, `split`, `blocked` ou `out-of-scope`.
6. Faça impact scan e atualize ADR, BL, CONTEXT, ROADMAP e dependências afetadas.
7. Grave rodada append-only e recalcule a fronteira inteira.

## Progresso e parada

Progresso observável é resolução/adiamento/bloqueio/split/out-of-scope, evidência nova, artefato atualizado ou gate de escopo fechado. Texto adicional sem alteração auditável não conta.

- Repetição de fingerprint: máximo duas; terceira ocorrência vira deferimento, bloqueio ou `SAFETY_STOP` conforme materialidade.
- Ambiguidade: uma clarificação por DQ; depois, bloqueie ou pare com segurança.
- Duas rodadas sem progresso, três expansões consecutivas ou 25 perguntas materiais acionam `SAFETY_STOP` e checkpoint.
- `stop/pause` grava `PAUSED_USER`.
- ADR/BL/evidência contraditórios abrem DQ de resolução; não sobrescreva silenciosamente.

`COMPLETE + GO` requer fronteira material sem `open|blocked`, auditoria GO e segunda passada sem DQ média/alta. `COMPLETE + NO-GO` é conclusão negativa válida, mas não libera handoff. `BLOCKED`, `SAFETY_STOP` e `PAUSED_USER` nunca liberam `ready-for-specify`.

## Checklist de mudança

- impacto classificado: emenda, exceção, substituição ou gate de escopo;
- ADR antigo/novo, backlinks, CONTEXT, BL, ROADMAP e DQ atualizados na mesma ação;
- fase usa `context-refs`, ADRs tocados, escopo, dependências e handoff exclusivo;
- nenhum `accepted` contraditório;
- rodada adicionada ao log sem alterar rodadas anteriores;
- auditoria emitida com GO/NO-GO/BLOCKED.
