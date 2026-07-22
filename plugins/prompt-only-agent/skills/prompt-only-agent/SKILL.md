---
name: prompt-only-agent
description: Entrevista curta para transformar uma ideia de agente em um system prompt pronto para copiar e colar. Use quando o usuário pedir um agente "prompt-only", system prompt ou instruções de sistema para um agente sem ferramentas, código, memória externa, RAG ou automações.
argument-hint: "<ideia ou objetivo do agente>"
---

# Prompt-Only Agent

Crie **um único system prompt em Markdown**, pronto para copiar e colar. O agente-alvo é **prompt-only**: não presuma ferramentas, arquivos, browser, memória persistente, RAG, APIs, automações, código executável ou acesso externo.

## Contrato

- Faça uma entrevista essencial e objetiva.
- Faça **uma pergunta por vez**, sempre com uma recomendação curta.
- A entrega é exclusivamente o system prompt autocontido, em Markdown.
- O system prompt copiado deve ter **no máximo 8.000 caracteres**, incluindo headings, espaços, quebras de linha e exemplos; o fence externo de entrega não entra nessa contagem.
- Trabalhe com meta de até **7.600 caracteres** para preservar margem e nunca entregue um prompt acima de 8.000 caracteres.
- Na resposta final, entregue somente o bloco de código copiável definido abaixo.

## Fase 1 — Descoberta

Use a ideia inicial como contexto e não repita o que já estiver claro. Faça apenas **uma pergunta atômica por mensagem**: se um tópico tiver mais de uma variável, pergunte-as em mensagens consecutivas. Pergunte somente quando necessário:

1. **Objetivo e usuário final** — Qual resultado concreto deve produzir, para quem e em qual idioma?
   - Recomendação: escolha um resultado observável, não uma atividade vaga.
2. **Entradas** — Quais informações o usuário fornecerá? Existe formato, contexto obrigatório ou exemplo?
   - Recomendação: liste apenas entradas que existirão na conversa; não invente fontes.
3. **Escopo** — O que deve fazer e o que fica explicitamente fora?
   - Recomendação: prefira uma responsabilidade principal e um encaminhamento claro.
4. **Saída** — Qual estrutura Markdown, tamanho, tom e nível técnico tornam a resposta boa?
   - Recomendação: use regras verificáveis, como “3 bullets”, em vez de “seja breve”.
5. **Limites e risco** — Que dados nunca pode inventar? Que aprovação, alerta ou fallback é necessário?
   - Recomendação: defina o comportamento para dados ausentes, ambíguos ou fora do escopo.
6. **Qualidade** — Há vocabulário, estilo, bom resultado ou mau resultado que deve orientar a resposta?
   - Recomendação: use até 2 exemplos, somente se eliminarem ambiguidade relevante.

Quando faltar apenas detalhe irrelevante, não prolongue a entrevista. Resuma o contrato em até 5 bullets; peça confirmação somente se uma decisão pendente mudar materialmente o prompt. Caso contrário, gere-o.

## Fase 2 — Construção

Escreva o prompt com estas seções, nesta ordem:

1. **Papel e objetivo** — identidade funcional e resultado.
2. **Contexto operacional** — público, idioma e entradas disponíveis.
3. **Responsabilidades** — ações permitidas.
4. **Restrições** — escopo e capacidades ausentes; nunca simule ferramentas ou acesso externo.
5. **Quando faltar informação ou o pedido sair do escopo** — fallback explícito.
6. **Formato da resposta** — estrutura Markdown, campos, tom e limites.
7. **Critérios de qualidade** — checks objetivos antes de responder.
8. **Exemplos** — no máximo 2, se indispensáveis.

## Regras de qualidade

- Dê instruções positivas, específicas e mensuráveis.
- Não prometa consultar dados, navegar, executar comandos, lembrar sessões ou enviar mensagens.
- Não invente políticas, fontes, SLAs, dados ou fatos; peça a informação mínima necessária ou declare a limitação.
- Evite persona decorativa, repetição e regras sem efeito observável.
- Não inclua `temperature` ou `top_p`, salvo pedido explícito.
- Não exponha raciocínio interno nem crie código, arquivos, workflow, RAG ou arquitetura.

## Formato final obrigatório

A resposta final deve conter **somente** este bloco preenchido. Não acrescente prefácio, explicação ou texto após o fence.

````markdown
```markdown
# System Prompt — [Nome do Agente]

## Papel e objetivo
...

## Contexto operacional
...

## Responsabilidades
...

## Restrições
...

## Quando faltar informação ou o pedido sair do escopo
...

## Formato da resposta
...

## Critérios de qualidade
...

## Exemplos (opcional; inclua somente se indispensáveis)
...
```
````

## Verificação

Antes de entregar, confirme que o prompt tem objetivo único e observável; usa apenas capacidades declaradas; define fallback; torna a saída verificável; não tem contradições, ferramentas implícitas ou texto de implementação; e está pronto para copiar sem edição estrutural.
