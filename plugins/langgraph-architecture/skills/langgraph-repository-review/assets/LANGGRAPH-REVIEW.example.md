# Revisão LangGraph — exemplo

## Veredito
`FINDINGS`

## Inventário
- `StateGraph`: `src/graph.py`
- Nodes: `chat`
- Checkpointer/Store: não encontrados

## Findings

### [LG-001] Conversa não persiste estado por thread
**Severidade:** P1

**Localização:** `src/graph.py:40`

**Evidência:** `compile()` é chamado sem checkpointer e o endpoint não fornece `thread_id`.

**Impacto:** cada turno perde contexto e produz respostas genéricas.

**Requisito mínimo violado:** short-term memory isolada por thread.

**Critério de aceite:** teste multi-turn prova retomada da mesma thread e isolamento entre duas threads.

## Checklist mínimo
| Item | Status |
|---|---|
| State tipado/reducers | OK |
| Checkpointer/thread_id | FAIL |
| Store/user namespace | UNVERIFIED |
| Grounding/RAG | FAIL |
| Quality gate/limites | FAIL |
| Evals final/trajectory/node | FAIL |

## Execução e limitações
Somente inspeção read-only; nenhum side effect foi executado.
