# Padrão LangGraph do usuário (referência destilada)

Fonte: wiki Obsidian do usuário — `Thinking in LangGraph`, `Padrão de Desenvolvimento com LangGraph`, `Workflow de Desenvolvimento de Agentes`.

## 0. Gate: quando **não** usar LangGraph

LangGraph é uma opção de orquestração, não a camada padrão de todo sistema com LLM. A decisão é **fail-closed**: sem uma razão estrutural, usar a primitiva mais simples.

| Sinal dominante | Escolha preferida |
|---|---|
| Daemon contínuo, I/O sub-segundo, captura de áudio | Serviço async/event loop do SO |
| Pipeline fixo por evento, reprocessamento, throughput | Fila + workers idempotentes + banco |
| Agendamento periódico | Cron/job scheduler |
| Read/write simples com integridade | Serviço + transação SQL |
| Consulta adaptativa com seleção de tools | LangGraph/agent loop |
| Workflow que revisa, retorna e retoma estado de forma adaptativa | LangGraph StateGraph |

**Nem retry granular, checkpoint, branches simples ou tracing justificam LangGraph isoladamente.** Eles podem ser fornecidos por workers, fila, banco e observabilidade comum.

LangGraph **não** fornece serialização entre execuções concorrentes, locks, idempotência de side effects nem garantia transacional. Essas responsabilidades pertencem à fonte de verdade/infraestrutura.

### Vereditos

- `SEM LANGGRAPH`: produzir Arquitetura Direta; sugerir “rodar o grill sem LangGraph”.
- `USO PARCIAL`: manter hot path determinístico fora e desenhar apenas o subfluxo adaptativo.
- `LANGGRAPH JUSTIFICADO`: seguir os passos abaixo.

## Thinking in LangGraph — 5 passos

1. **Mapear como passos discretos.** Cada passo = um node (função, faz UMA coisa). Não otimizar agora; primeiro mapear, depois refinar.
2. **Identificar o tipo de cada passo** e, para LLM steps, separar contexto estático (prompt) de contexto dinâmico (state) e resultado desejado.
3. **Projetar o State** (Regra CRUE).
4. **Construir os nodes** (lê state → trabalha → retorna updates).
5. **Conectar** via Regra de Ouro; nodes roteiam via `Command`.

## Tipos de node

| Tipo | Quando usar | Exemplo |
|---|---|---|
| **LLM step** | Entender, analisar, gerar, decidir | Classificar intent, gerar resposta |
| **Data step** | Recuperar fonte externa | Buscar docs, consultar banco |
| **Action step** | Ação externa | Enviar email, criar ticket |
| **User-input step** | Intervenção humana | Aprovação, correção |
| **Router** | Lê status/flag e decide | Retomada pós-handoff |

## Regra CRUE — State

State guarda **dados brutos**, nunca texto de prompt. Prompts são montados dentro dos nodes. Para cada dado: precisa persistir entre passos? → state. Pode ser derivado? → computar on-demand.

Campos frequentes: `status` e `mensagens` (com sumarização definida). Não use State LangGraph para substituir tabelas/eventos operacionais externos.

## Regra de Ouro — escolha de aresta

| Situação | Mecanismo | Retorno |
|---|---|---|
| Destino único fixo | `add_edge` | `dict` |
| Um de N decidido em runtime | `Command[Literal[...]]` | `Command(goto=..., update=...)` |
| Fan-out paralelo | `Command` + `Send` | `Send(...)` |

## Agent-as-node vs nodes explícitos

| Use agent-as-node | Use nodes explícitos |
|---|---|
| Caminho imprevisível | Fluxo determinístico fixo |
| Loop de tool-calling | Checkpoint/retry isolado por passo |
| LLM escolhe próxima tool com base no retorno | Decisão pontual de 1 entre N destinos |

Fluxo fixo não vira agente. LLM precisa de loop → agente encapsulado em um node.

## Controle de fluxo — State-Check

Para handoff humano, node seta `status="aguardando_humano"`, emite mensagem e vai a `END`. Na próxima invocação, Router lê status e retoma. `interrupt()` fica reservado a input pontual, se necessário, e deve ser primeira operação do node.

## Tratamento de erro

| Erro | Estratégia |
|---|---|
| Transiente | `RetryPolicy` no node/worker correto |
| Recuperável por LLM | Guardar erro e voltar ao loop |
| Informação faltante | State-Check humano |
| Inesperado | `raise` + observabilidade |

## 6 padrões de workflow

1. Prompt Chaining
2. Parallelization
3. Routing
4. Orchestrator-Worker
5. Evaluator-Optimizer
6. Agent loop

Um fluxo real pode combinar padrões, mas isso não substitui o gate de adequação.
