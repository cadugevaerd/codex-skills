---
name: langgraph-architecture-plan
description: Cria um plano verificável de arquitetura LangGraph para chat ou agentes. Deve delegar integralmente a análise ao agente isolado langgraph-architect e garantir contexto, memória, grounding, quality gate, limites, observabilidade e evals mínimos.
argument-hint: "[repo=/caminho] [objetivo e restrições]"
---

# Plano de Arquitetura LangGraph

Use esta skill para projetar ou evoluir a arquitetura de um sistema LangGraph. Ela é **plan-only**: produz um plano e não implementa código.

## Delegação isolada obrigatória

O agente principal não deve criar o plano por conta própria.

1. Localize a raiz do repositório e preserve o pedido original do usuário.
2. Invoque exatamente um agente dedicado e espere sua conclusão:
   - Claude Code: subagente `langgraph-architecture:langgraph-architect` pelo tool `Agent`.
   - Codex: custom agent `langgraph_architect` em uma thread de subagente.
3. Passe ao agente o pacote completo: caminho do repositório, objetivo, restrições, runtime, requisitos de latência/custo, fontes de conhecimento e riscos conhecidos.
4. O agente deve trabalhar em contexto isolado. Não replique a análise no contexto principal.
5. Se o papel dedicado não estiver disponível, retorne `BLOCKED` com a etapa de instalação; **não** faça fallback para o agente principal ou para um agente genérico.
6. Preserve no retorno os gaps, riscos, evidências e decisões produzidos pelo agente.

## Contrato mínimo que o plano deve garantir

O agente arquiteto deve inspecionar o repositório antes de propor mudanças e rastrear cada afirmação a arquivos, símbolos, configuração ou documentação oficial. O plano deve cobrir, ou justificar explicitamente como `N/A`, todos os itens:

### Grafo e estado

- entrypoints, `StateGraph`/subgraphs, nodes, edges e condições;
- state explícito e tipado, reducers e ownership de cada campo;
- separação entre dados brutos de estado e texto derivado pelo modelo;
- `agent/generate`, `tools` ou retrieval e `quality_gate` como baseline lógico;
- router apenas quando domínios, políticas, modelos ou toolsets realmente diferirem;
- limites de iteração, retries, timeouts, recursion limit e rotas de erro/fallback.

### Contexto e memória

- prompt dinâmico por domínio, usuário, estágio e permissões;
- short-term memory com checkpointer e isolamento por `thread_id`;
- long-term memory com store e namespace por `user_id`/tenant;
- política de trimming ou summarization para contexto longo;
- recuperação seletiva de memórias relevantes, sem despejar todo o histórico.

### Grounding e tools

- RAG, banco ou APIs para fatos privados, atuais ou verificáveis;
- decisão explícita entre 2-Step, Agentic ou Hybrid RAG;
- tools com nomes, descrições, argumentos, permissões e erros claros;
- seleção restrita/dinâmica de tools para evitar overload e ações indevidas;
- citações/proveniência e comportamento `não sei` quando a evidência for insuficiente.

### Qualidade, segurança e operação

- quality gate seletivo para intenção, completude, grounding, evidência e formato;
- retry de revisão limitado; ambiguidade material deve virar pergunta ao usuário;
- HITL e confirmação para efeitos irreversíveis ou de alto risco;
- isolamento de side effects e idempotência onde aplicável;
- tracing de runs, traces e threads, com versão de prompt/modelo/grafo;
- evals em três níveis: resposta final, trajetória e node isolado;
- dataset inicial com 5–10 exemplos curados por componente crítico;
- métricas de qualidade, groundedness, retrieval, tool use, custo e latência.

## Formato obrigatório do plano

O agente deve criar `LANGGRAPH-ARCHITECTURE-PLAN.md` na raiz indicada, salvo caminho diferente solicitado, e também devolver o Markdown integral ao agente principal. Se o runtime mantiver as alterações do subagente apenas no worktree isolado, o agente principal pode persistir **exatamente** o artefato devolvido no caminho combinado, sem reescrever, completar ou certificar o conteúdo. O plano deve conter:

1. `Status e escopo`
2. `Evidências do estado atual`
3. `Requisitos e restrições`
4. `Arquitetura proposta` com Mermaid
5. `State schema e reducers`
6. `Tabela de nodes e edges`
7. `Contexto, memória e grounding`
8. `Tools, permissões e side effects`
9. `Quality gate, retries, HITL e limites`
10. `Observabilidade e evals`
11. `Plano incremental de implementação`
12. `Matriz requisito → mudança → teste/evidência`
13. `Riscos, decisões e perguntas abertas`

## Gate de conclusão

Somente reporte `READY` quando todos os itens mínimos estiverem cobertos ou marcados `N/A` com justificativa verificável. Use `BLOCKED` se o repositório estiver inacessível, faltar contexto indispensável ou a evidência não permitir um plano confiável. Nunca invente arquivos, execução, métricas ou comportamento do grafo.
