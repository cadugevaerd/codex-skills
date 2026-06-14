---
name: grillme-langgraph
description: Interroga o usuário (estilo grill-me) sobre um processo e produz o rascunho de um fluxo LangGraph — diagrama do grafo, schema do State (CRUE), tabela de nodes com explicação de cada um, e a marcação de quais trechos são determinísticos vs não-determinísticos dentro do fluxo maior determinístico. Use SEMPRE que o usuário quiser desenhar, projetar, rascunhar ou planejar um grafo/agente LangGraph, decompor um processo em nodes, decidir onde o fluxo é fixo vs onde o LLM decide, ou mencionar "grillme langgraph", "grill langgraph", "desenhar o fluxo", "projetar nodes", "agent-as-node vs nodes explícitos", "fluxo determinístico e não determinístico". Dispara mesmo que o usuário não diga "LangGraph" explicitamente, desde que esteja descrevendo um agente/workflow com passos, decisões e handoff humano.
---

# grillme-langgraph

Esta skill projeta o **rascunho de um fluxo LangGraph** a partir de um processo descrito pelo usuário. Ela trabalha em duas fases:

1. **Grilling** — interroga o usuário, uma pergunta de cada vez, até resolver toda a árvore de decisão do fluxo.
2. **Design** — produz o desenho do grafo, o schema do State e a tabela de nodes com explicação de cada um.

A saída é **design + diagrama, sem código de implementação**. O objetivo é o usuário sair com um rascunho claro o suficiente para implementar (ou pedir a implementação) depois.

O padrão de referência é o do próprio usuário, destilado em `references/padrao-langgraph.md`. **Leia esse arquivo antes de começar** — ele contém o modelo mental "Thinking in LangGraph", a Regra CRUE de State, a Regra de Ouro de escolha de aresta, a decisão agent-as-node vs nodes explícitos, o padrão State-Check (não `interrupt()`) e os 6 padrões de workflow. Tudo o que você produzir deve seguir esse padrão.

## Conceito central: determinístico dentro de um fluxo maior determinístico

O grafo externo é **determinístico**: nodes explícitos, arestas fixas conhecidas em tempo de design, roteamento de paradas/handoff via **State-Check** (uma flag `status` no state, nunca `interrupt()`). Dentro dele existem **bolsões de não-determinismo** — pontos onde o destino só é conhecido em runtime porque um LLM decide. A skill existe para ajudar o usuário a separar com clareza os dois e escolher o mecanismo certo para cada um.

Mapeie cada passo a uma destas três categorias — isso vira a coluna "Determinismo" da tabela de nodes:

| Categoria | Como o destino é decidido | Mecanismo |
|---|---|---|
| **DET** (determinístico) | Fixo em tempo de design — sempre o mesmo próximo node | `add_edge` |
| **NÃO-DET / roteado** | Runtime escolhe 1 de N destinos via lógica ou 1 chamada de LLM | `Command[Literal["a","b"]]` |
| **NÃO-DET / agente** | Caminho imprevisível, precisa de loop de tool-calling | Agent-as-node (`create_agent`) encapsulado num único node |

Regra de decisão para a fronteira do não-determinismo: se o caminho é imprevisível **e** precisa de um loop LLM→tools→LLM, encapsule num **agent-as-node**. Se é só "escolher 1 de N destinos com uma decisão pontual", mantenha **nodes explícitos + `Command[Literal]`**. Não transforme um fluxo fixo em agente — isso é over-engineering (ver `references/padrao-langgraph.md`).

## Fase 1 — Grilling

Interrogue **uma pergunta de cada vez**, sempre com a sua resposta recomendada anexada (estilo da skill `grill-me` do usuário). Se uma pergunta puder ser respondida lendo o projeto/codebase ou a wiki, investigue em vez de perguntar. Desça cada galho da árvore antes de subir para o próximo. Não avance para o design enquanto restar ambiguidade que mude o desenho.

Cubra estes galhos, nesta ordem (adapte — pule o que já estiver respondido no contexto):

1. **Objetivo e escopo.** Qual é o processo, em uma frase? Onde ele começa (entrada) e termina (saída/`END`)?
2. **Passos discretos.** Quais são as ações distintas? (Ainda sem otimizar — primeiro mapear, depois refinar.) Liste-os.
3. **Tipo de cada passo.** Para cada um: LLM step, Data step, Action step, User-input step, ou Router. (Ver tabela em `references/padrao-langgraph.md`.)
4. **Determinismo de cada passo.** Para cada passo: o destino é fixo (DET → `add_edge`), runtime escolhe 1 de N (NÃO-DET roteado → `Command[Literal]`), ou é um caminho imprevisível com loop de tools (NÃO-DET agente → agent-as-node)? Esta é a pergunta-chave da skill — resolva-a para todo passo.
5. **Fronteiras dos agentes.** Onde a imprevisibilidade realmente justifica um agent-as-node em vez de nodes explícitos? Cheque contra a tabela de tradeoffs. Resista a transformar fluxo fixo em agente.
6. **Handoff humano (HITL).** Onde o fluxo para e espera um humano? Confirme o padrão **State-Check**: o node seta `state["status"] = "aguardando_humano"`, emite a mensagem e vai para `END`; a próxima invocação bate num node roteador que lê `status`. Nunca `interrupt()` para handoff.
7. **State (Regra CRUE).** Quais **dados brutos** precisam persistir entre passos? (Nada de texto de prompt formatado no state — prompts são montados dentro do node.) Inclua a flag `status` e, se houver histórico de conversa, a estratégia de sumarização a cada N mensagens.
8. **Tratamento de erro.** Há pontos que precisam de `RetryPolicy` (transiente), loop de auto-correção do LLM (recuperável), ou subir `raise` (inesperado)?
9. **Padrão dominante.** Qual dos 6 padrões descreve o fluxo principal (Prompt Chaining, Parallelization, Routing, Orchestrator-Worker, Evaluator-Optimizer, Agent loop)? Pode haver um padrão externo com sub-padrões internos.

Quando a árvore estiver resolvida, faça um resumo de 3-5 linhas do que entendeu e confirme antes de desenhar.

## Fase 2 — Design (a saída)

Produza a saída seguindo `assets/template-saida.md`. Ela tem 5 seções, nesta ordem:

1. **Resumo do fluxo** — 2-3 frases: objetivo, entrada, saída, padrão dominante.
2. **Diagrama (Mermaid)** — um `flowchart TD` do grafo, de `START` a `END`. Use a convenção visual:
   - Nodes **DET** com caixa retangular `["nome"]`.
   - Nodes **NÃO-DET roteado** com losango/decisão e arestas rotuladas com a condição.
   - Nodes **agent-as-node** com subrotina `[["nome (agente)"]]`.
   - Marque pontos de **State-Check / HITL** com uma aresta para `END` rotulada `status=aguardando_humano`.
3. **Schema do State (CRUE)** — tabela: campo | tipo | descrição. Apenas dados brutos. Inclua `status` e a flag/estrutura de roteamento. Anote o que é derivado e **não** deve ser armazenado.
4. **Tabela de nodes** — uma linha por node: `Node | Tipo | Determinismo (DET / NÃO-DET roteado / NÃO-DET agente) | Mecanismo de aresta (add_edge / Command[Literal] / Send) | Responsabilidade (1 frase)`.
5. **Explicação de cada node** — um parágrafo curto por node: o que lê do state, o que faz, o que retorna, e — para os não-determinísticos — quais são os destinos possíveis e o que decide entre eles.

Feche com uma seção curta **"Decisões em aberto / riscos"** listando qualquer ambiguidade que sobrou ou trade-off que o usuário deveria revisitar.

Não escreva código de implementação. Se o usuário pedir o esqueleto Python depois, aí sim gere — mas a entrega-padrão desta skill é o design.

## Princípios (por quê)

- **Mapear antes de otimizar** (Passo 1): force a decomposição completa antes de discutir agente vs nodes. Decisões de granularidade tomadas cedo demais viram over-engineering.
- **State-Check, não `interrupt()`**: é a convenção firme do usuário para handoff — roteável, inspecionável, e sobrevive a reinícios sem prender a execução. `interrupt()` fica reservado para coleta de input pontual dentro de um node, quando muito.
- **Regra CRUE**: dados brutos no state, prompt montado no node. Mantém o schema estável quando os prompts mudam e deixa o debug claro.
- **A fronteira det/não-det é a entrega**: o valor desta skill é o usuário ver, node a node, onde ele cedeu controle ao LLM e por quê. Torne essa fronteira explícita no diagrama e na tabela.
