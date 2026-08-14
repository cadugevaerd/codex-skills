---
name: langgraph-repository-review
description: Revisa um repositório que usa LangGraph e lista problemas de arquitetura, contexto, memória, grounding, tools, qualidade, segurança, observabilidade e evals. Deve delegar integralmente a revisão ao agente isolado e read-only langgraph-reviewer.
argument-hint: "[repo=/caminho] [escopo opcional]"
---

# Revisão de Repositório LangGraph

Use esta skill para auditar uma implementação LangGraph existente. O contrato é **review-only**: localizar problemas com evidência, sem modificar arquivos ou corrigir o repositório.

## Delegação isolada obrigatória

O agente principal não deve revisar o código por conta própria.

1. Localize a raiz do repositório e o escopo solicitado.
2. Invoque exatamente um agente dedicado e espere sua conclusão:
   - Claude Code: subagente `langgraph-architecture:langgraph-reviewer` pelo tool `Agent`.
   - Codex: custom agent `langgraph_reviewer` em uma thread de subagente.
3. Passe caminho, branch/base quando aplicável, objetivo do sistema e restrições conhecidas.
4. O revisor deve operar em contexto isolado e read-only. Não autorize edição, commit, push ou correção.
5. Se o papel dedicado não estiver disponível, retorne `BLOCKED` com a etapa de instalação; não use agente genérico como fallback.
6. O agente principal pode formatar o resultado, mas não remover evidências, incertezas ou findings.

## Procedimento obrigatório do revisor

1. Confirme que o repositório realmente usa LangGraph e identifique versões e entrypoints.
2. Mapeie `StateGraph`/subgraphs, nodes, edges condicionais, interrupts, checkpointer, store, tools/retrievers e interfaces de entrada/saída.
3. Trace ao menos um caminho conversacional representativo e os caminhos de erro/retry.
4. Leia testes, evals, tracing e configuração de produção; não conclua pela presença de nomes de arquivos.
5. Liste somente problemas sustentados por evidência reproduzível em `arquivo:linha`, símbolo, comando ou configuração.
6. Não execute side effects reais. Testes devem usar sandbox, fake, dry-run ou fixtures seguras.

## Checklist mínimo

O revisor deve verificar:

- state tipado, reducers corretos, ownership e ausência de overwrite/lost updates;
- nodes e edges alcançáveis, rotas END/erro e loops limitados;
- baseline lógico `agent/generate ↔ tools/retrieval → quality_gate`, ou justificativa válida;
- router apenas quando existe especialização real;
- prompt/contexto específico em vez de apenas “helpful assistant”;
- checkpointer persistente em produção e isolamento correto por `thread_id`;
- store de longo prazo separado e namespace por `user_id`/tenant;
- trimming/summarization e recuperação seletiva de memória;
- RAG/tools para fatos privados/atuais, relevância do retrieval, grounding e proveniência;
- descrições, argumentos, permissões, timeouts e tratamento de erro dos tools;
- quality gate seletivo, retry limitado, fallback e perguntas de esclarecimento;
- HITL/confirmação, idempotência e isolamento de side effects;
- observabilidade de runs/traces/threads e metadata de versão;
- evals de resposta final, trajetória e node isolado;
- dataset curado com 5–10 exemplos por componente crítico e cobertura de casos ambíguos, sem evidência e falha de tool;
- segurança: prompt injection em documentos, segredo/PII, autorização e tenant isolation;
- compatibilidade async/sync, concorrência, custo e latência.

## Severidade e formato

Ordene findings por severidade:

- `P0`: risco imediato de segurança, perda de dados ou ação irreversível indevida;
- `P1`: resposta incorreta/não fundamentada, isolamento quebrado ou fluxo essencial defeituoso;
- `P2`: fragilidade relevante de qualidade, operação, testes ou observabilidade;
- `P3`: melhoria justificável sem impacto material imediato.

Cada finding deve conter:

```text
[LG-###] Título
Severidade:
Localização:
Evidência:
Impacto:
Requisito mínimo violado:
Critério de aceite:
```

Finalize com:

- `Veredito: PASS | FINDINGS | BLOCKED`
- inventário dos componentes encontrados;
- checklist mínimo `OK | FAIL | N/A | UNVERIFIED`;
- limitações e comandos/testes realmente executados.

Não publique comentário, não altere arquivos e não invente execução. Ausência de evidência deve ser `UNVERIFIED` ou `BLOCKED`, nunca aprovação.
