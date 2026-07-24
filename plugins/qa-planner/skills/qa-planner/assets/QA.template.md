# QA Plan

<!-- qa-planner:start -->
## 1. Identificação

| Campo | Valor |
|---|---|
| Status do plano | READY \| PARTIAL \| BLOCKED |
| Repositório | `<nome>` |
| Raiz analisada | `<caminho>` |
| Branch alvo | `<branch>` |
| Base | `<base>` |
| HEAD SHA | `<sha>` |
| Range de diff | `<merge-base>..HEAD` |
| Alterações locais incluídas | `sim \| não` |
| Caminho do QA.md | `<caminho>` |
| Justificativa do local | `<motivo>` |

## 2. Evidências consultadas

| ID | Fonte | Tipo | O que comprova |
|---|---|---|---|
| EVD-001 | `<path/URL>` | requisito \| diff \| instrução \| teste \| CI | `<fato observável>` |

## 3. Requisitos e critérios de aceite

| ID | Status | Requisito / critério de aceite | Evidência |
|---|---|---|---|
| REQ-001 | confirmado \| inferido | `<comportamento observável>` | EVD-001 |

## 4. Rastreabilidade

| Requisito / risco | Cenários | Prioridade |
|---|---|---|
| REQ-001 | QA-001, QA-002 | P0 |

## 5. Escopo e fora de escopo

### No escopo

- `<área/fluxo>`

### Fora de escopo

- `<área/fluxo e motivo>`

## 6. Estratégia de testes

| Risco | Probabilidade | Impacto | Prioridade | Abordagem |
|---|---|---|---|---|
| RISK-001 — `<risco>` | baixa \| média \| alta | baixo \| médio \| alto | P0 \| P1 \| P2 | `<nível/tipo de teste>` |

- **Critério de entrada:** `<pré-requisito para a execução>`
- **Critério de saída:** `<condição para encerrar a execução>`

## 7. Ambiente, dados e dependências

| Item | Necessidade | Fonte / observação |
|---|---|---|
| Ambiente | `<staging/local/etc.>` | `<evidência ou TBD>` |
| Dados | `<massa/conta/tenant>` | `<evidência ou TBD>` |
| Dependência | `<serviço/feature flag>` | `<evidência ou TBD>` |

## 8. Cenários detalhados

### QA-001 — `<título objetivo>`

- **Rastreabilidade:** REQ-001; RISK-001
- **Prioridade:** P0
- **Nível/tipo:** API
- **Automação:** recomendada
- **Status inicial:** NOT_RUN
- **Pré-condições e dados:** `<estado verificável>`
- **Passos:**
  1. `<ação>`
- **Resultado esperado:** `<resultado observável>`
- **Evidência a coletar:** `<assertion, response, log, screenshot ou métrica>`
- **Comando/harness candidato:** `TBD — não encontrado nas evidências`

## 9. Regressão necessária

- `<fluxo/regra relacionada e motivo>`

## 10. Candidatos à automação

| Cenário | Camada sugerida | Local/harness candidato | Motivo |
|---|---|---|---|
| QA-001 | API | `<evidência ou TBD>` | `<estabilidade e valor>` |

## 11. Dúvidas, suposições e bloqueios

- **Pergunta:** `<lacuna que impede certeza>`
- **Impacto:** `<cenário ou risco afetado>`
- **Origem:** `<evidência>`

## 12. Handoff para a IA executora

1. Confirme que branch e `HEAD SHA` ainda correspondem à seção 1.
2. Execute somente os cenários `QA-*` aplicáveis.
3. Registre comando, entrada, saída real, evidência e timestamp em `QA-RESULTS.md`.
4. Preserve `QA.md` como plano; não substitua cenários por resultados.
5. Use somente `PASS`, `FAIL`, `BLOCKED` ou `SKIPPED` em `QA-RESULTS.md`.
6. Se ambiente, dados ou dependência estiver indisponível, registre `BLOCKED`; nunca invente resultado.

Planejamento de QA encerrado. Nenhum teste foi executado.
<!-- qa-planner:end -->
