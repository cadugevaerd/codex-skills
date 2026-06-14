# Padrão LangGraph do usuário (referência destilada)

Fonte: wiki Obsidian do usuário — `Thinking in LangGraph`, `Padrão de Desenvolvimento com LangGraph`, `Workflow de Desenvolvimento de Agentes`. Este é o padrão que toda saída da skill deve seguir.

## Thinking in LangGraph — 5 passos

1. **Mapear como passos discretos.** Cada passo = um node (função, faz UMA coisa). Não otimizar agora; primeiro mapear, depois refinar.
2. **Identificar o tipo de cada passo** (tabela abaixo) e, para LLM steps, separar contexto estático (prompt) de contexto dinâmico (do state) e o resultado desejado.
3. **Projetar o State** (Regra CRUE).
4. **Construir os nodes** (função: lê state → trabalha → retorna apenas updates). Tratamento de erro em 4 categorias.
5. **Conectar (wire)** via Regra de Ouro de arestas. A estrutura do grafo emerge; nodes roteiam a si mesmos via `Command`.

## Tipos de node

| Tipo | Quando usar | Exemplo |
|---|---|---|
| **LLM step** | Entender, analisar, gerar, decidir | Classificar intent, gerar resposta |
| **Data step** | Recuperar de fonte externa | Buscar docs, consultar banco |
| **Action step** | Executar ação externa | Enviar email, criar ticket |
| **User-input step** | Intervenção humana | Aprovação, correção |
| **Router** | Ler `status`/flag e decidir caminho | Roteador de retomada pós-handoff |

## Regra CRUE — State

O State guarda **dados brutos**, nunca texto formatado. Prompts são montados dentro de cada node a partir dos dados crus.

```
ERRADO:  state["prompt"] = "Classifique este email: Fui cobrado duas vezes..."
CERTO:   state["email_content"] = "Fui cobrado duas vezes..."
         state["classification"] = {"intent": "billing", "urgency": "critical"}
         # prompt montado DENTRO do node: f"Classifique: {state['email_content']}"
```

Para cada dado pergunte: precisa persistir entre passos? → state. Pode ser derivado? → computar on-demand, não armazenar.

Campos quase sempre presentes:
- `status` (str): flag que roteia o grafo. Ex.: `"coletando_requisitos"`, `"aguardando_humano"`, `"concluido"`.
- `mensagens` (list): histórico bruto. Definir estratégia de sumarização a cada N mensagens para poupar context window.

## Regra de Ouro — escolha de aresta

| Situação | Mecanismo | Como retornar |
|---|---|---|
| Destino único, sempre o mesmo (DET) | `add_edge` | `return dict` — o builder já enxerga a aresta |
| Destino dinâmico, 1 de N por lógica/LLM (NÃO-DET) | `Command[Literal["a","b"]]` | `return Command(goto=destino, update={...})` |
| Fan-out paralelo, N simultâneos | `Command` + `Send` | `return Command(goto=[Send("node", payload), ...])` |

Decisão: destino fixo em design → `add_edge`. Runtime decide → `Command[Literal]`. N em paralelo com payloads diferentes → `Send`.

## Agent-as-node vs nodes explícitos

| Use agent-as-node | Use nodes explícitos |
|---|---|
| Caminho imprevisível | Fluxo determinístico fixo |
| Precisa de loop de tool-calling | Checkpoint granular necessário |
| Vários nodes LLM sem justificativa | RetryPolicies diferentes por passo |

Regra: fluxo fixo → nodes explícitos. LLM precisa decidir num loop → agente encapsulado como um node (`create_agent`). **Não** transforme fluxo fixo em agente — é o erro de over-engineering mais comum.

## Controle de fluxo — State-Check (NÃO `interrupt()` para handoff)

Para handoff humano use **state-based routing**: o node seta `state["status"] = "aguardando_humano"`, emite a mensagem e vai para `END`. A próxima invocação cai num node **Router** que lê `status` e retoma o caminho certo. Isso é roteável, inspecionável e sobrevive a reinícios.

`interrupt()` fica reservado para coleta de input pontual dentro de um node (e, se usado, DEVE ser a primeira operação do node, porque o código antes dele re-executa ao resumir). Para o padrão de parada/aprovação do usuário, sempre State-Check.

## Tratamento de erro — 4 categorias

| Erro | Quem resolve | Estratégia |
|---|---|---|
| Transiente (rede, rate limit) | Sistema | `RetryPolicy(max_attempts, initial_interval)` no registro do node |
| Recuperável por LLM (tool fail, JSON quebrado) | LLM | Guardar erro no state, voltar ao loop para o LLM corrigir |
| Resolvível pelo usuário (info faltando) | Humano | State-Check (`status=aguardando_humano`) |
| Inesperado | Dev | `raise` — sobe para o log de debug |

## Granularidade de nodes

Nodes menores = mais checkpoints = menos retrabalho em falha. Checkpoints são async — mais nodes **não** significa mais lento. Separe em nodes distintos quando: chamada a serviço externo (isolar falha), ponto de decisão (visibilidade), retry diferente, ou parte reutilizável.

## 6 padrões de workflow

1. **Prompt Chaining** — `A → gate → B → C → END`. Sequência decomponível em passos verificáveis.
2. **Parallelization** — `START → [A,B,C] → aggregator → END`. Subtasks independentes (velocidade/confiança).
3. **Routing** — `START → router → [A|B|C] → END`. Direciona para fluxo especializado.
4. **Orchestrator-Worker** — `START → orchestrator → [workers...] → synthesizer → END`. Subtarefas dinâmicas via Send API.
5. **Evaluator-Optimizer** — `generate → evaluate → [aceito:END | rejeitado:generate]`. Refinamento iterativo.
6. **Agent loop** — `llm_call → [tools? → tool_node → llm_call | no_tools → END]`. Máxima autonomia.

Um fluxo real costuma ser um padrão externo (ex.: Prompt Chaining com gates por fase) com sub-padrões internos (ex.: um node que é um Evaluator-Optimizer ou um agent loop).
