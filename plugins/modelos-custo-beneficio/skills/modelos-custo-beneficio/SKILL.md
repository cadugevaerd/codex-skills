---
name: "modelos-custo-beneficio"
description: "Seleciona até 5 candidatos OpenRouter para Model Engineering Eval com reasoning controlável, variantes :exacto/:nitro e throughput hard >=60 t/s (p75; p50 fallback). Não executa Eval nem muda runtime."
argument-hint: "tool_calls=true|false input=<text,image,file> structured_outputs=true throughput_min=60 [limit=2..5]"
---

# Modelos custo-benefício — candidatos para Eval

Use quando o usuário precisar encontrar modelos OpenRouter para avaliar com requisitos técnicos. Esta skill **não decide o modelo de produção** e **não cria/roda o Model Engineering Eval**: ela devolve somente candidatos e o guia de execução no runner já existente do repositório.

## Contrato obrigatório

Todo candidato deve cumprir simultaneamente:

1. Ser a versão mais recente de sua família (heurística `created` do OpenRouter).
2. Não ser modelo/variante gratuita.
3. Declarar reasoning controlável via `reasoning.supported_efforts` ou `reasoning.supports_max_tokens`.
4. Ter endpoint OpenRouter com `throughput_last_30m.p75 >= 60 t/s`; quando `p75` não existir, usar `p50` (ou `median`/`avg`) como fallback. Dado ausente **reprova** o endpoint.
5. Cumprir capacidades solicitadas: inputs, Tool Calls, structured outputs, contexto e teto de custo.

Não use throughput da Artificial Analysis para satisfazer o filtro hard. `--use-artificial-analysis` é opcional e só pode enriquecer a ordenação preliminar.

## Roteamento por tipo de tarefa

| Necessidade | Flag | Slug emitido |
|---|---|---|
| A tarefa exige Tool Calls | `--tool-calls` | `<modelo>:exacto` |
| A tarefa é apenas geração textual | `--no-tool-calls` | `<modelo>:nitro` |

`--no-tool-calls` escolhe `:nitro`; não elimina modelos que também sejam capazes de chamar tools.

## Entrada

Converta texto livre em flags. Aceite também `--requirements-json`.

| Parâmetro | Flag | Observação |
|---|---|---|
| `throughput_min` / `min_throughput` | `--min-throughput` | Piso fixo: 60; valores menores são rejeitados. |
| `input`, `input_types` | `--input` | Ex.: `text,image` |
| `output` | `--output` | Ex.: `text` |
| `tool_calls=true` | `--tool-calls` | Exige `tools` no endpoint. |
| `tool_calls=false` | `--no-tool-calls` | Rota `:nitro`. |
| `structured_outputs=true` | `--structured-outputs` | Exige `structured_outputs`, não só `response_format`. |
| `min_context` | `--min-context` | Janela mínima. |
| `max_cost_per_1m` | `--max-cost-per-1m` | Teto ponderado. |
| `limit` | `--limit` | Aceita 2–5; padrão 5. |

## Procedimento

1. Execute o seletor; não recomende modelos de memória.

   ```bash
   # Não exponha credenciais em saída/log.
   OPENROUTER_API_KEY="$(op item get 'OpenRouter API Key' --vault 'Automação' --fields credential --reveal)" \
   python scripts/openrouter_model_recommender.py \
     --limit 5 \
     --min-throughput 60 \
     --input text,image \
     --tool-calls \
     --structured-outputs \
     --min-context 128000
   ```

2. Interprete o resultado apenas como lista de candidatos para a suíte de Eval local. Se houver 2–4 candidatos, liste todos. Se houver menos de 2, pare: não relaxe automaticamente os requisitos nem invente candidatos.

3. No Model Engineering Eval do repositório, teste cada candidato no reasoning inicial:
   - `supported_efforts`: comece em `xhigh`, ou no maior nível suportado;
   - `supports_max_tokens`: aplique o mapa local de tokens para começar no equivalente a `xhigh`.

4. Uma configuração só passa com `pass_rate >= 95%`, salvo limiar explicitamente definido pela suíte local. Registre provider efetivo, payload de reasoning, custo real, latência e throughput.

5. Para cada modelo que passar, reduza o esforço um nível por vez:

   ```text
   xhigh → high → medium → low → minimal
   ```

   Pule níveis não suportados. Ao primeiro nível que falhar, retenha o menor nível anterior aprovado para aquele modelo. Continue o fluxo mesmo que reste apenas um sobrevivente.

6. Se pelo menos dois modelos distintos passarem, o **Eval** define:

   ```text
   principal = menor custo total observado
               → menor latência
               → maior throughput

   fallback  = próximo modelo distinto aprovado
   ```

   Aplique o resultado no runtime manualmente; esta skill não altera configuração de produção.

7. Revalide no prazo configurado (padrão: 30 dias) ou antes quando houver mudança de modelo, provider, preço, controle de reasoning ou suíte de Eval.

## Saída

Entregue **somente**:

- até cinco modelos/variantes candidatos, com endpoint, configuração inicial de reasoning e throughput usado (`p75` ou fallback `p50`);
- o guia de execução do Eval acima.

Não anuncie vencedor, não exponha ranking como decisão final e não sugira throughput desconhecido como aceitável.
