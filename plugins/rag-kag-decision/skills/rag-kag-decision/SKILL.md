---
name: rag-kag-decision
description: "Decide quando usar RAG, KAG, GraphRAG ou arquitetura híbrida para sistemas LLM com conhecimento externo."
argument-hint: "<descrição do caso, fontes de dados, risco, exemplos de perguntas>"
---

# RAG vs KAG Decision

Use esta skill quando precisar decidir se um sistema com LLM deve usar **RAG**, **KAG**, **GraphRAG** ou abordagem **híbrida**.

## Regra de bolso

```text
RAG = recuperar conhecimento textual.
KAG = raciocinar sobre conhecimento estruturado.
GraphRAG = usar grafo para melhorar recuperação/contexto, sem necessariamente ter motor lógico completo.
```

## Processo obrigatório

Antes de recomendar, classifique o caso:

1. **Fonte da verdade**: documentos, banco estruturado, KG, APIs, ERP/CRM/CMDB?
2. **Tipo de pergunta**: direta, multi-hop, regra, cálculo, temporalidade, compliance?
3. **Entidades**: existem objetos centrais como cliente, contrato, ativo, usuário, produto, norma, chamado?
4. **Relações**: a resposta depende de vínculos entre entidades?
5. **Risco do erro**: baixo, médio ou alto?
6. **Atualização**: muda rápido ou exige consistência semântica?
7. **Maturidade**: existe time/dado para manter ontologia/grafo?

## Matriz de decisão

| Sinal observado | Escolha preferida |
|---|---|
| PDFs, wikis, manuais, tickets e FAQs | RAG |
| Perguntas respondidas por poucos trechos | RAG |
| MVP rápido / baixo custo inicial | RAG |
| Base textual muda diariamente | RAG |
| Precisa citar trechos originais | RAG |
| Entidades e relações são o núcleo | KAG |
| Perguntas multi-hop são comuns | KAG |
| Regras, datas, vigência, permissões ou cálculos importam | KAG |
| Domínio crítico: jurídico, saúde, financeiro, compliance | KAG |
| RAG perde contexto por relações, mas KAG completo é caro | GraphRAG |
| Documentos + dados estruturados são ambos necessários | Híbrido RAG + KAG |

## Quando usar RAG em detrimento de KAG

Escolha **RAG** quando:

- o problema é achar, citar e resumir texto;
- a base é predominantemente documental;
- perguntas são diretas;
- atualização rápida importa mais que consistência lógica;
- não há ontologia/grafo confiável;
- o time precisa de MVP verificável.

Exemplos: chat com documentação interna, FAQ de suporte, busca em procedimentos, copiloto para manuais, triagem inicial de contratos.

## Quando usar KAG em detrimento de RAG

Escolha **KAG** quando:

- a resposta depende de entidades e relações;
- há regras de negócio, compliance, datas ou cálculos;
- perguntas multi-hop são frequentes;
- precisa explicar o caminho lógico, não só citar fonte;
- erros custam caro;
- já existe fonte estruturada ou é viável criar/manter KG.

Exemplos: elegibilidade de cliente por contrato+plano+fatura+SLA, análise jurídica com prazos/obrigações, saúde com contraindicações, ITSM com ativos/usuários/chamados/SLA, compliance auditável.

## Padrão recomendado

Se não há prova de que RAG falha, recomende evolução incremental:

```text
1. Comece com RAG bem feito: chunking, metadados, busca híbrida, reranker e citações.
2. Meça falhas: entidade confundida, regra ignorada, data errada, multi-hop ruim.
3. Adicione GraphRAG/KAG nas fatias críticas.
```

## Arquiteturas mínimas

### RAG mínimo

```text
Documentos → chunking → embeddings/vector DB → retrieval/rerank → prompt com citações → LLM
```

### KAG mínimo

```text
Fontes → extração/curadoria de entidades e relações → KG + índice textual → reasoning híbrido → contexto estruturado → LLM
```

### Híbrido pragmático

```text
RAG recupera evidências textuais
KG/KAG valida entidades, regras e relações
LLM produz resposta final com fontes + caminho lógico
```

## Formato de saída

Responda sempre com:

````markdown
## Decisão
**Escolha:** RAG | KAG | GraphRAG | Híbrido

## Por quê
- sinal 1
- sinal 2
- sinal 3

## Arquitetura mínima
```text
...
```

## Riscos
- ...

## Quando reavaliar/migrar
- ...
````

## Fontes conceituais

- Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, NeurIPS 2020 / arXiv:2005.11401.
- Liang et al., *KAG: Boosting LLMs in Professional Domains via Knowledge Augmented Generation*, arXiv:2409.13731.
- OpenSPG/KAG: reasoning/retrieval guiado por forma lógica sobre KG + LLM.
