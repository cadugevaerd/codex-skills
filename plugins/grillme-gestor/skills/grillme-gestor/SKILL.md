---
name: grillme-gestor
description: Versão não-técnica da grillme-langgraph. Entrevista um gestor ou profissional não-técnico sobre um processo usando APENAS perguntas de negócio (sem jargão), e produz EXATAMENTE a mesma saída técnica que a grillme-langgraph — diagrama do grafo LangGraph, schema do State (CRUE), tabela de nodes determinístico vs não-determinístico, e explicação de cada node — entregue como um arquivo markdown. Use quando o usuário for um gestor/cliente que precisa descrever um processo para virar uma automação, quando pedir uma "versão para o gestor", "versão não-técnica", "briefing para enviar", ou mencionar "grillme gestor". O usuário descreve o processo em linguagem de negócio; VOCÊ faz toda a tradução para o design técnico.
---

# grillme-gestor

Esta skill é a **versão não-técnica da `grillme-langgraph`**. A única diferença está na **forma de perguntar**: o entrevistado é um gestor que não conhece termos técnicos. A **saída é idêntica** — o mesmo rascunho de fluxo LangGraph (diagrama + State CRUE + tabela de nodes det/não-det + explicação de cada node).

A tradução do negócio para o design técnico é **sua responsabilidade**, não do gestor. Ele responde "o que acontece no processo"; você decide o que vira node, qual é DET vs NÃO-DET, onde entra agent-as-node, onde é State-Check para handoff, e o que é o State.

O padrão técnico de referência está em `references/padrao-langgraph.md`. **Leia esse arquivo antes de começar** — modelo "Thinking in LangGraph", Regra CRUE de State, Regra de Ouro de arestas, agent-as-node vs nodes explícitos, padrão State-Check (não `interrupt()`), e os 6 padrões de workflow. Tudo o que você produzir segue esse padrão.

## Regra de ouro da entrevista: nunca use jargão técnico

Proibido nas perguntas: "node", "state", "LangGraph", "grafo", "determinístico", "agente", "LLM", "aresta", "API", "endpoint", "função", "roteamento", "handoff", "interrupt", "código". O gestor fala de **trabalho, pessoas, decisões, sistemas e documentos**. Você mapeia internamente cada resposta para o conceito técnico correspondente (ver tabela de tradução abaixo).

## Tabela de tradução (interna — não mostre ao gestor)

Use isto para converter as respostas de negócio no design técnico:

| O gestor descreve... | Você modela como... |
|---|---|
| Uma ação distinta no processo | um **node** |
| "Sempre depois disso vem aquilo" | aresta **DET** (`add_edge`) |
| "Depende do caso: se A faz X, se B faz Y" (regra clara ou julgamento pontual) | **NÃO-DET roteado** (`Command[Literal]`) |
| "O sistema tenta sozinho, mexe em várias coisas, até resolver" (caminho imprevisível com várias tentativas/ferramentas) | **NÃO-DET agente** (agent-as-node) |
| "Analisar/entender/redigir/classificar/decidir" | **LLM step** |
| "Buscar/consultar/puxar informação de algum lugar" | **Data step** |
| "Enviar/criar/registrar/executar algo externo" | **Action step** |
| "Para e espera uma pessoa aprovar/responder/assinar" | **State-Check** (`status="aguardando_humano"` → `END`) + node **Router** na retomada |
| "As informações que preciso guardar entre as etapas" | campos do **State** (Regra CRUE — só dado bruto) |
| "Se der erro de conexão / instabilidade" | `RetryPolicy` |
| "Se a informação veio errada, tenta de novo" | loop de auto-correção do LLM |
| "Falta informação, precisa de alguém" | State-Check (`aguardando_humano`) |

## Fase 1 — Entrevista (linguagem de negócio)

Faça **uma pergunta de cada vez**, sempre com uma sugestão de resposta entre parênteses para destravar. Se algo já foi respondido, não repita. Investigue o projeto/codebase/wiki antes de perguntar, se a resposta estiver lá. Desça cada assunto até o fim antes de mudar de tema. Não avance para o documento enquanto restar ambiguidade que mude o desenho.

Cubra estes temas, nesta ordem (adapte e pule o que já estiver claro). Entre colchetes está o galho técnico que cada pergunta resolve — **não mostre os colchetes ao gestor**:

1. **Objetivo e limites.** Em uma frase, o que esse processo faz? O que faz ele começar e quando você considera que ele terminou? *[objetivo, START, END]*
2. **Passo a passo.** Conte, na ordem, tudo o que acontece do início ao fim — como se estivesse ensinando alguém novo. (Ainda sem detalhar; primeiro a sequência.) *[decomposição em nodes — mapear antes de otimizar]*
3. **Natureza de cada passo.** Para cada passo, ele é: analisar/decidir/redigir algo, buscar uma informação, executar uma ação (enviar/registrar), ou esperar uma pessoa? *[tipo de node: LLM / Data / Action / User-input / Router]*
4. **Caminhos e decisões.** Em quais momentos o processo pode seguir por caminhos diferentes? O que decide qual caminho? É uma regra clara (ex.: valor acima de X) ou depende de análise caso a caso? *[DET vs NÃO-DET roteado — a pergunta-chave]*
5. **Passos "complicados".** Algum passo é do tipo "o sistema precisa se virar sozinho, tentando coisas diferentes até conseguir", sem um caminho fixo? Ou todos os passos têm um próximo passo previsível? *[fronteira do agent-as-node — resista a transformar fluxo fixo em agente]*
6. **Esperas por pessoas.** Em quais pontos o processo trava esperando alguém (aprovar, assinar, responder)? O que essa pessoa precisa fazer para destravar? *[State-Check / HITL — confirmar padrão status=aguardando_humano, nunca interrupt()]*
7. **Informações que ficam guardadas.** Quais informações precisam ser lembradas de uma etapa para a outra? (Foque no dado em si — ex.: "o valor do pedido", "o histórico do cliente" — não em textos prontos.) *[State, Regra CRUE — só dado bruto + flag status; estratégia de sumarização se houver histórico de conversa]*
8. **Quando dá errado.** O que costuma falhar? Quando falha, o sistema deveria: tentar de novo sozinho, pedir ajuda de uma pessoa, ou parar e avisar? *[4 categorias de erro: RetryPolicy / auto-correção / State-Check / raise]*
9. **Formato geral.** (Você decide internamente.) Qual dos 6 padrões descreve o fluxo principal e se há sub-padrões. *[padrão dominante]*

Quando resolver tudo, faça um **resumo de 3-5 linhas em linguagem de negócio** do que entendeu e confirme com o gestor antes de gerar o documento. (No resumo, ainda sem jargão.)

## Fase 2 — Documento (saída técnica — IDÊNTICA à grillme-langgraph)

Produza a saída seguindo **exatamente** `assets/template-saida.md` e **salve como arquivo markdown** para o gestor poder enviar. As 5 seções, nesta ordem:

1. **Resumo do fluxo** — 2-3 frases: objetivo, entrada, saída, padrão dominante.
2. **Diagrama (Mermaid)** — `flowchart TD` de `START` a `END`. Convenção visual:
   - Node **DET**: retângulo `["nome"]`.
   - Node **NÃO-DET roteado**: losango/decisão, arestas rotuladas com a condição.
   - Node **agent-as-node**: subrotina `[["nome (agente)"]]`.
   - Ponto de **State-Check / HITL**: aresta para `END` rotulada `status=aguardando_humano`.
3. **Schema do State (CRUE)** — tabela: campo | tipo | descrição. Só dado bruto. Inclui `status` e a flag de roteamento. Anote o que é derivado e **não** se armazena.
4. **Tabela de nodes** — `Node | Tipo | Determinismo (DET / NÃO-DET roteado / NÃO-DET agente) | Mecanismo de aresta (add_edge / Command[Literal] / Send) | Responsabilidade`.
5. **Explicação de cada node** — um parágrafo curto por node: o que lê do state, o que faz, o que retorna; para os não-determinísticos, os destinos possíveis e o que decide entre eles.

Feche com **"Decisões em aberto / riscos"** listando ambiguidades e trade-offs que o gestor/desenvolvedor deveria revisitar.

Não escreva código de implementação. A entrega é o design técnico em markdown.

### Entrega como arquivo

Salve a saída em um arquivo `.md` (ex.: `fluxo-{nome-do-processo}.md`) no diretório de trabalho atual e informe o caminho ao usuário, para que ele anexe e envie. Se não houver diretório de trabalho claro, salve em `~/fluxo-{nome-do-processo}.md`.

## Princípios

- **Perguntas de negócio, design técnico.** O gestor nunca vê jargão; a saída é 100% o design LangGraph da `grillme-langgraph`.
- **A tradução é sua.** Não peça ao gestor para classificar passos como DET/não-DET ou escolher entre agent-as-node e nodes explícitos — isso você infere das respostas e checa contra `references/padrao-langgraph.md`.
- **Mapear antes de otimizar.** Force a decomposição completa (pergunta 2) antes de decidir granularidade ou agente vs nodes.
- **State-Check, não `interrupt()`** para qualquer espera por pessoa.
- **A fronteira det/não-det é a entrega.** Mesmo que o gestor não use os termos, o documento final deve deixar explícito, node a node, onde o controle foi cedido ao LLM e por quê.
