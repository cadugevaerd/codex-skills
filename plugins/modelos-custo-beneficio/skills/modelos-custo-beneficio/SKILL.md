---
name: "modelos-custo-beneficio"
description: "Seleciona os 5 modelos LLM mais custo-beneficio, sempre tentando manter a ultima versao por familia, filtrando por throughput minimo, modalidades de input/output, Tool Calls, structured outputs, contexto e custo. Usa OpenRouter em tempo real e Artificial Analysis opcional quando houver AA_API_KEY."
argument-hint: "throughput_min=<tokens/s> input=<text,image,file> tool_calls=true structured_outputs=true min_context=<tokens> [limit=5]"
---

# Modelos custo-beneficio — selector de LLM sem chute

Use esta skill quando o usuario pedir modelos com melhor custo-beneficio e requisitos tecnicos como:

- throughput minimo;
- tipos de input (`text`, `image`, `file`, `audio`, `video`);
- Tool Calls / function calling;
- saida estruturada (`structured_outputs` / JSON Schema);
- contexto minimo;
- teto de custo.

A resposta deve trazer **5 modelos por padrao** e deve preferir a **ultima versao por familia de modelo**. Modelo velho barato e sedutor continua sendo velho. O Império chamava isso de legado; aqui chamamos de risco.

## Entrada / parametros aceitos

O usuario pode passar parametros em texto livre ou em pares `chave=valor`. Converta para flags do script.

| Parametro do usuario | Flag do script | Exemplo |
|---|---|---|
| `throughput_min`, `min_throughput` | `--min-throughput` | `throughput_min=50` |
| `input`, `input_types`, `modalidades` | `--input` | `input=text,image,file` |
| `output`, `output_modalities` | `--output` | `output=text` |
| `tool_calls` | `--tool-calls` / omitido | `tool_calls=true` |
| `structured_outputs`, `saida_estruturada` | `--structured-outputs` / omitido | `structured_outputs=true` |
| `min_context`, `context_min` | `--min-context` | `min_context=128000` |
| `max_cost_per_1m` | `--max-cost-per-1m` | `max_cost_per_1m=3` |
| `limit` | `--limit` | `limit=5` |

Tambem aceite JSON:

```bash
python scripts/openrouter_model_recommender.py \
  --requirements-json '{"throughput_min":50,"input_types":["text","image"],"tool_calls":true,"structured_outputs":true}'
```

## Procedimento obrigatorio

1. Rode o script desta skill. Nao tente ranquear modelo de memoria.

   ```bash
   # Se OPENROUTER_API_KEY nao estiver no ambiente, carregar do 1Password sem imprimir:
   OPENROUTER_API_KEY="$(op item get 'OpenRouter API Key' --vault 'Automação' --fields credential --reveal)" \
   python scripts/openrouter_model_recommender.py \
     --limit 5 \
     --min-throughput 50 \
     --input text,image \
     --tool-calls \
     --structured-outputs \
     --min-context 128000
   ```

2. Se o usuario pedir throughput minimo e o OpenRouter nao publicar `throughput_last_30m` suficiente:
   - primeiro valide se ha `OPENROUTER_API_KEY`; sem chave o endpoint pode retornar dados incompletos;
   - se `AA_API_KEY` ou `ARTIFICIAL_ANALYSIS_API_KEY` existir, rode com `--use-artificial-analysis`;
   - se nao existir, explique que o filtro de throughput ficou bloqueado por falta de dado publico e ofereca `--allow-unknown-throughput` **com ressalva explicita**.

3. Preserve a semantica de requisitos:
   - Tool Calls = `tools` nos `supported_parameters` do endpoint;
   - saida estruturada = `structured_outputs`, nao apenas `response_format`;
   - input types = `architecture.input_modalities` precisa conter todas as modalidades exigidas;
   - latest = filtro heuristico por familia + maior `created` do OpenRouter.

4. Entregue tabela curta com:
   - modelo (`model_id`), provider/endpoint;
   - inputs;
   - Tool Calls sim/nao;
   - Structured Outputs sim/nao;
   - contexto;
   - throughput e fonte;
   - custo input/output e custo ponderado por 1M;
   - motivo do ranking.

## Exemplos

### Texto + imagem, tools e structured outputs

```bash
python scripts/openrouter_model_recommender.py \
  --min-throughput 40 \
  --input text,image \
  --tool-calls \
  --structured-outputs \
  --min-context 128000
```

### Aceitar throughput desconhecido, mas penalizar score

```bash
python scripts/openrouter_model_recommender.py \
  --min-throughput 40 \
  --allow-unknown-throughput \
  --input text \
  --tool-calls \
  --structured-outputs
```

### JSON como parametro da skill

```bash
python scripts/openrouter_model_recommender.py \
  --requirements-json '{"throughput_min":80,"input_types":["text","file"],"tool_calls":true,"structured_outputs":true,"min_context":200000}'
```

## Regras de saida

- Seja direto: top 5 e ressalvas. Sem palestra.
- Nao recomende modelo que falhou em requisito hard.
- Se menos de 5 modelos passarem, diga quantos passaram e qual filtro provavelmente estreitou demais.
- Se usar `--allow-unknown-throughput`, marque os modelos com throughput desconhecido. Dados ausentes nao viram performance por magia, infelizmente.
