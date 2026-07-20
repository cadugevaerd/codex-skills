# Fixture — Timbro: uso parcial de LangGraph

## Cenário

O Timbro é um agente desktop que escuta microfone e saída do sistema enquanto Teams, Zoom ou Meet ocorrem. Ele processa janelas efêmeras, persiste eventos e permite perguntas ao conteúdo confirmado durante a chamada.

## Veredito esperado

`USO PARCIAL`

| Fluxo | Decisão | Razão |
|---|---|---|
| Captura, alinhamento e ring buffer | SEM LANGGRAPH | daemon de baixa latência e I/O do SO |
| Janela: STT → seleção → recorte → ECAPA → commit | SEM LANGGRAPH | pipeline fixo por evento; workers idempotentes e PostgreSQL fornecem retry, estado e auditoria |
| Reconciliação de cluster | SEM LANGGRAPH | requer serialização/lock/constraint transacional entre execuções |
| Consulta LLM durante a chamada | LANGGRAPH JUSTIFICADO | LLM pode decidir iterativamente quais tools de busca/intervalo/speaker chamar |
| HITL de nomeação | SEM LANGGRAPH | comando transacional + evento |

## Fronteira

```text
Eventos committed/provisional no PostgreSQL
  → consulta LangGraph (read-only + tools de recuperação)
  → resposta com timestamps e estado da evidência
```

O LangGraph não é responsável por captura, processamento das janelas, locks de cluster ou promoção transacional.
