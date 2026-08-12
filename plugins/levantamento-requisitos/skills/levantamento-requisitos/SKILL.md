---
name: levantamento-requisitos
description: Levanta requisitos verificáveis e entrega um handoff pronto para implementar sem suposições ocultas.
argument-hint: "<pedido do projeto> [source=<URLs|arquivos>] [output=<path>]"
---

# Levantamento de Requisitos — discovery antes de implementar

Use esta skill antes de planejar ou implementar um projeto, feature, integração ou mudança relevante. O objetivo é produzir o **mínimo suficiente, verificável e rastreável** para que Carlos implemente sem descobrir depois um requisito implícito importante.

```text
pedido → evidências → perguntas de alto impacto → decisões/assunções → aceite → handoff → STOP
```

## Contrato

- É **discovery-only**: não implemente, não altere código, configuração, infraestrutura, dados, branches, PRs ou tickets.
- Não invente requisitos, APIs, prazos, decisões ou comportamento. Diferencie sempre `CONFIRMADO`, `ASSUMIDO`, `EM ABERTO` e `BLOQUEADO`.
- Comece pelas fontes fornecidas. Quando houver repositório acessível, leia instruções locais, documentação, contratos, interfaces e testes existentes somente para coletar evidência.
- Faça perguntas apenas quando a resposta mudar escopo, arquitetura, segurança, custo, prazo, aceite ou operação. Agrupe perguntas independentes e priorize-as.
- Se uma resposta não estiver disponível, registre a lacuna e o impacto; não a esconda em texto genérico.
- Ao final, entregue o documento de requisitos e pare. A implementação pertence a um próximo workflow.

## Entradas e evidências

| Entrada | Uso |
|---|---|
| Pedido inicial | Objetivo, resultado esperado e urgência declarada. |
| `source` | URLs, documentos, tickets, PRs, APIs, protótipos ou caminhos fornecidos. Cite-os. |
| Repositório acessível | Instruções, arquitetura, contratos e comportamento atual; código é evidência do estado atual, não prova de intenção futura. |
| Stakeholders | Nomeie decisor, usuário/operador e aprovador quando conhecidos; senão, marque em aberto. |

Para cada requisito ou decisão, registre a fonte. Prioridade de autoridade:

1. decisão explícita do Carlos ou do dono de negócio;
2. contrato/documento aprovado;
3. interface, ticket ou PR fornecido;
4. comportamento verificável existente;
5. inferência, sempre marcada como `ASSUMIDO`.

Se fontes divergirem, preserve a divergência como decisão aberta e não escolha silenciosamente.

## Roteiro de levantamento

### 1. Delimite o problema

Registre, em linguagem de negócio:

- problema e resultado desejado;
- usuário(s), operador(es) e decisor(es);
- gatilho, frequência e jornada principal;
- escopo e fora de escopo;
- restrições já conhecidas: prazo, orçamento, stack, ambiente, compatibilidade e dependências.

Transforme pedidos vagos em resultado observável. Exemplo: não use “integrar sistema”; use “quando X ocorrer, Y deve receber Z em até N, com falha visível e reprocessável”.

### 2. Faça a varredura anti-surpresa

Para cada item aplicável, registre `decidido`, `não aplicável` ou uma pergunta/lacuna com impacto:

| Dimensão | O que confirmar |
|---|---|
| Funcional | fluxos feliz, alternativos, exceções, regras e limites. |
| Usuário e acesso | papéis, autenticação, autorização, tenant/isolamento e aprovação humana. |
| Dados | origem, campos, qualidade, retenção, LGPD, propriedade, histórico e exclusão. |
| Integrações | dono, contrato, autenticação, rate limit, timeout, retry, idempotência e reconciliação. |
| Falhas | mensagens, recuperação, fallback, fila/reprocessamento e comportamento parcial. |
| Segurança | segredos, menor privilégio, auditoria, ameaça relevante e compliance. |
| Operação | ambiente, deploy, feature flag, configuração, observabilidade, alertas e suporte. |
| Mudança | migração/backfill, compatibilidade, rollout, rollback e custo. |
| Qualidade | desempenho, disponibilidade, acessibilidade, testes e critérios mensuráveis. |

Não aplique o checklist como burocracia: omita apenas com justificativa `NÃO APLICÁVEL`.

### 3. Pergunte pelo que bloqueia ou muda a solução

Classifique cada pergunta:

- `P0 — BLOQUEIA`: impede definir comportamento, segurança, dados, integração, aceite ou responsável.
- `P1 — ALTO IMPACTO`: pode alterar arquitetura, esforço, custo, prazo ou risco.
- `P2 — PODE SER POSTERGADA`: não impede um fatiamento seguro; registre a decisão provisória.

Use perguntas fechadas ou com opções quando isso acelerar uma decisão. Para cada pergunta, inclua: contexto, opções/consequências quando houver, dono da resposta e prazo/condição de bloqueio.

### 4. Converta em contrato implementável

Crie IDs estáveis:

- `REQ-001...` para requisitos funcionais ou não funcionais;
- `AC-001...` para critérios de aceite;
- `DEC-001...` para decisões;
- `ASM-001...` para suposições;
- `Q-001...` para perguntas abertas;
- `RISK-001...` para riscos/dependências.

Todo `REQ-*` deve conter comportamento observável, origem, prioridade e ligação a um ou mais `AC-*`. Não use termos não testáveis como “rápido”, “seguro” ou “simples” sem medida, limite ou responsável.

### 5. Determine prontidão

Use somente um destes vereditos:

- `READY`: objetivo, escopo, responsáveis, requisitos críticos, aceite e riscos/dependências estão definidos; não há `Q-001` P0 aberta.
- `PARTIAL`: existe um corte seguro para implementar, mas há lacunas P1/P2 explícitas e um responsável para resolvê-las.
- `BLOCKED`: existe uma pergunta P0, conflito de fontes, dependência indisponível ou falta de decisão que torna a implementação arriscada.

`READY` não significa que toda preferência foi decidida; significa que as incertezas remanescentes não podem invalidar o corte implementável definido.

## Formato obrigatório de saída

Entregue um único documento Markdown, salvo no `output` fornecido se houver; se não houver caminho explicitamente autorizado, apresente o conteúdo na conversa e não crie arquivo.

```markdown
# Levantamento de Requisitos — <projeto>

## 1. Veredito de prontidão
- **Status:** READY | PARTIAL | BLOCKED
- **Corte implementável:** ...
- **Motivo e próximo decisor:** ...

## 2. Problema, resultado e stakeholders
## 3. Escopo e fora de escopo
## 4. Evidências consultadas
## 5. Requisitos
### REQ-001 — <título>
- **Status:** CONFIRMADO | ASSUMIDO
- **Prioridade:** P0 | P1 | P2
- **Comportamento observável:** ...
- **Evidência:** ...
- **Aceite:** AC-001, AC-002

## 6. Critérios de aceite
### AC-001 — <resultado verificável>
- **Dado/ação:** ...
- **Resultado esperado:** ...
- **Evidência de aceite:** ...

## 7. Regras, dados, integrações e operação
## 8. Decisões e suposições
## 9. Perguntas abertas
## 10. Riscos, dependências e mitigação
## 11. Handoff para implementação
- **Primeiro corte:** ...
- **Contratos/artefatos a criar ou alterar:** ...
- **Validações obrigatórias:** ...
- **Não fazer:** ...
```

Em `## 11`, liste apenas insumos reais para o próximo implementador: fronteiras, contratos, dados, validações e decisões pendentes. Não produza plano de código detalhado nem inicie execução.

## Gate final

Antes de entregar:

- todo requisito tem fonte/status e aceite observável;
- toda inferência está marcada como `ASSUMIDO`;
- toda dimensão aplicável da varredura anti-surpresa foi decidida ou virou lacuna explícita;
- perguntas P0 impedem `READY`;
- o handoff identifica o corte implementável, riscos e validações;
- não há implementação disfarçada de levantamento.

Termine exatamente com:

```text
Levantamento encerrado. Nenhuma implementação foi iniciada.
```
