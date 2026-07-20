---
name: grillme-langgraph
description: Entrevista técnica (estilo grill-me) para decidir primeiro se LangGraph é justificado e, somente quando for, desenhar o fluxo LangGraph com diagrama, State CRUE e tabela de nodes. Use quando o usuário quiser desenhar agentes/workflows, avaliar se LangGraph é excesso de engenharia, decidir agent-as-node vs nodes explícitos, ou separar um hot path determinístico de uma consulta/agente adaptativo.
argument-hint: "descreva o processo, objetivo, entrada, saída e restrições de latência/estado"
---

# grillme-langgraph

Esta skill não presume que todo workflow merece LangGraph. Ela trabalha em três modos:

1. **Gate de adequação** — determina se LangGraph é justificado.
2. **Grilling sem LangGraph** — quando o fluxo é daemon, pipeline fixo, worker, fila ou transação, produz a arquitetura direta adequada.
3. **Design LangGraph** — somente para o subfluxo que de fato requer estado de grafo, roteamento adaptativo ou loop LLM→tools→LLM.

A entrega padrão é design + diagrama, sem código de implementação.

## Fonte de referência

Leia `references/padrao-langgraph.md` antes de começar. Ela contém o modelo “Thinking in LangGraph”, Regra CRUE, Regra de Ouro de arestas, State-Check, fronteira determinística/não-determinística e o gate “quando não usar LangGraph”.

## Fase 0 — Gate de adequação (obrigatório)

Antes de falar em nodes, faça uma pergunta por vez e investigue o que puder no projeto/documentação. Resolva:

1. **Caminho crítico.** É daemon contínuo, captura/streaming de baixa latência, job por evento, consulta sob demanda ou processo humano longo?
2. **Fluxo real.** Passos e destinos são conhecidos em design ou variam materialmente em runtime?
3. **LLM.** Há ciclo imprevisível `LLM → tools → LLM`, ou apenas chamada pontual de LLM/classificação?
4. **Estado.** Há estado que precisa pausar/retomar entre interações? Não é melhor representado por tabelas/eventos no banco?
5. **Coordenação.** Há concorrência, idempotência, locks, serialização, rate limiting ou transações? Declare a fonte de verdade; não atribua essas garantias ao LangGraph.
6. **Falhas.** Retry/checkpoint por etapa são conveniência ou razão estrutural? Filas/workers já resolvem isso?
7. **Alternativa mínima.** Qual é a opção mais simples: função/serviço async, fila + workers, cron, banco transacional, ou um agente/tool loop?

### Veredito fail-closed

Só recomende LangGraph se houver razão estrutural explícita:

```text
✓ loop imprevisível LLM → tools → LLM;
✓ workflow adaptativo com revisão/retorno em runtime;
✓ estado durável, retomável e mais claro como grafo;
✓ subfluxo conversacional que escolhe dados/ferramentas dinamicamente.
```

Não use LangGraph como resposta automática a:

```text
✗ daemon contínuo ou captura sub-segundo;
✗ pipeline fixo de ingestão/processamento;
✗ retry, rate limit, scheduling ou observabilidade;
✗ idempotência de side effect;
✗ lock, serialização ou integridade transacional entre execuções;
✗ branches determinísticas simples.
```

### Saída do gate

Declare um veredito antes de continuar:

| Veredito | Próximo passo |
|---|---|
| **SEM LANGGRAPH** | Diga: “recomendo rodar o grill sem LangGraph”. Continue no modo Arquitetura Direta e use `assets/template-sem-langgraph.md`. Não invente State CRUE, nodes ou Mermaid de LangGraph. |
| **USO PARCIAL** | Separe fluxos: hot path determinístico fora; rode o grilling LangGraph somente no subfluxo justificado. Produza ambos os desenhos e a fronteira explícita. |
| **LANGGRAPH JUSTIFICADO** | Continue para Fase 1 e gere o design completo. |

Em qualquer veredito, explique evidências, alternativa mínima, o que LangGraph resolveria (se usado) e o que ele **não** resolveria.

## Modo Arquitetura Direta — SEM LANGGRAPH

Quando o gate retornar `SEM LANGGRAPH`, continue uma pergunta por vez até fechar:

1. entrada, saída e SLA/latência;
2. unidade idempotente e chave de deduplicação;
3. daemon/fila/worker/cron;
4. fonte de verdade, transação, lock e concorrência;
5. retries por classe de falha e DLQ/reprocessamento;
6. observabilidade, métricas e auditoria;
7. gatilho futuro que poderia justificar um subfluxo LangGraph.

Produza `assets/template-sem-langgraph.md`. Não chame a alternativa de “grafo simplificado”; nomeie a primitiva concreta: serviço async, worker, fila, banco, cron ou chamada de função.

## Fase 1 — Grilling LangGraph

Execute somente para o escopo aprovado no gate. Faça uma pergunta por vez, com recomendação anexada, e desça cada galho antes de avançar:

1. objetivo, entrada, saída/`END` e fronteira fora do grafo;
2. passos discretos; mapear antes de otimizar;
3. tipo: LLM, Data, Action, User-input ou Router;
4. determinismo: fixo (`add_edge`), roteado (`Command[Literal]`) ou loop de tools (agent-as-node);
5. agent-as-node somente para `LLM → tools → LLM`; decisão pontual usa nodes explícitos;
6. HITL via State-Check, nunca `interrupt()` como padrão;
7. State CRUE: apenas dados brutos; prompts nos nodes;
8. falhas: retry transiente, loop recuperável, State-Check humano ou `raise`;
9. padrão dominante: Prompt Chaining, Parallelization, Routing, Orchestrator-Worker, Evaluator-Optimizer ou Agent loop.

Antes do design, resuma em 3–5 linhas e confirme que o escopo do grafo permanece justificado.

## Fase 2 — Saídas

### Para LANGGRAPH JUSTIFICADO

Use `assets/template-saida.md`, nesta ordem:

1. Parecer de adequação e fronteira com componentes fora do grafo.
2. Resumo do fluxo.
3. Diagrama Mermaid.
4. Schema do State (CRUE).
5. Tabela de nodes.
6. Explicação de cada node.
7. Decisões em aberto/riscos.

### Para USO PARCIAL

Entregue primeiro o parecer e o desenho Arquitetura Direta do hot path. Depois gere o template LangGraph só para o subfluxo justificado. Declare a interface: evento/entrada, contrato de dados, idempotency key, dono da transação e SLA.

## Princípios

- **Decidir antes de modelar.** A primeira entrega é adequação, não diagrama.
- **Menor primitiva suficiente.** Fluxo fixo continua função, worker ou fila mesmo com branches, retries e métricas.
- **LangGraph não substitui infraestrutura.** Locks/serialização pertencem ao banco; retries/scheduling podem pertencer à fila; captura de baixa latência pertence ao daemon.
- **CRUE só dentro do grafo.** Não force State LangGraph sobre estado operacional no banco.
- **Fronteiras explícitas.** Se apenas consulta adaptativa precisa de LangGraph, não contamine o hot path.
