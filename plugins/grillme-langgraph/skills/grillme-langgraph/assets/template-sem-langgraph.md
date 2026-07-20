# Parecer de Arquitetura Direta — {NOME DO FLUXO}

## 0. Veredito

- **Decisão:** `SEM LANGGRAPH`
- **Recomendação:** rodar o grill sem LangGraph.
- **Motivo:** {o fluxo é fixo/contínuo/operacional; não há loop adaptativo LLM→tools→LLM ou estado de grafo necessário.}
- **Primitiva escolhida:** {serviço async | fila + workers | cron | função | transação SQL}
- **Gatilho de reavaliação:** {condição concreta para introduzir apenas um subfluxo LangGraph no futuro.}

## 1. Fluxo operacional

```text
{entrada} → {serviço/fila/worker} → {persistência/ação} → {saída}
```

## 2. Contrato e estado

| Item | Decisão |
|---|---|
| Unidade de trabalho | `{...}` |
| Idempotency key | `{...}` |
| Fonte de verdade | `{...}` |
| Transação/lock | `{...}` |
| Concorrência | `{...}` |
| Retenção/versão | `{...}` |

## 3. Falhas e reprocessamento

| Classe | Estratégia |
|---|---|
| Transiente | `{retry/backoff}` |
| Permanente | `{DLQ/review}` |
| Duplicata | `{deduplicação}` |
| Inesperado | `{alerta/log}` |

## 4. Observabilidade e SLA

- **Métricas:** {latência E2E, throughput, erro, backlog, custo...}
- **Auditoria:** {eventos/artefatos persistidos}
- **SLA:** {valor e comportamento sob degradação}

## 5. Limites e futura fronteira LangGraph

- {O que continua fora: locks, banco, captura, scheduling...}
- {Subfluxo futuro que poderia usar LangGraph e sua interface de entrada/saída.}
