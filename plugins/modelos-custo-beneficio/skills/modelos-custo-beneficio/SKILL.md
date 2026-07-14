---
name: "modelos-custo-beneficio"
description: "Seleciona até 5 candidatos OpenRouter para Model Engineering Eval com reasoning controlável, variantes :exacto/:nitro e throughput hard >=60 t/s. Aprovação exige gates de idioma nativo, Markdown, Tool Calls e antialucinação."
argument-hint: "eval_language=<BCP-47> tool_calls=true|false input=<text,image,file> structured_outputs=true throughput_min=60 [limit=2..5]"
---

# Modelos custo-benefício — candidatos para Eval

Use para encontrar candidatos OpenRouter conforme requisitos técnicos. Esta skill **não escolhe modelo de produção** e não executa o runner: devolve até cinco candidatos e o contrato obrigatório para a suíte de Eval do repositório.

## Contrato de descoberta

Todo candidato deve cumprir simultaneamente:

1. versão mais recente da família (heurística `created` do OpenRouter);
2. não gratuito;
3. reasoning controlável via `reasoning.supported_efforts` ou `reasoning.supports_max_tokens`;
4. endpoint com `throughput_last_30m.p75 >= 60 t/s`; na ausência de `p75`, `p50`/`median`/`avg` é fallback. Dado ausente reprova;
5. inputs, structured outputs, contexto e teto de custo solicitados;
6. suporte a `tools`, pois o gate de Tool Calls é obrigatório inclusive para runtime textual.

Não use throughput da Artificial Analysis para satisfazer o filtro hard. `--use-artificial-analysis` só enriquece ordenação preliminar.

## Roteamento

| Necessidade de runtime | Flag | Slug emitido |
|---|---|---|
| Runtime exige Tool Calls | `--tool-calls` | `<modelo>:exacto` |
| Runtime apenas textual | `--no-tool-calls` | `<modelo>:nitro` |

`--no-tool-calls` define o slug de runtime; ele **não** dispensa o gate obrigatório de Tool Calls, que deve testar o mesmo modelo com `:exacto`.

## Entrada

`eval_language` é obrigatório e deve representar o idioma nativo da aplicação, por exemplo `pt-BR`. Aceite texto livre convertido para flags ou `--requirements-json`.

| Requisito | Flag | Observação |
|---|---|---|
| idioma nativo | `--eval-language` | obrigatório; exemplo `pt-BR` |
| throughput | `--min-throughput` | piso fixo de 60 t/s |
| input | `--input` | `text,image`, por exemplo |
| runtime com Tools | `--tool-calls` | emite `:exacto` |
| runtime texto | `--no-tool-calls` | emite `:nitro`; mantém gate Tools |
| structured output | `--structured-outputs` | exige `structured_outputs` |
| contexto | `--min-context` | janela mínima |
| custo | `--max-cost-per-1m` | teto ponderado |
| candidatos | `--limit` | 2–5; padrão 5 |

## Procedimento obrigatório

1. Execute o seletor sem expor segredos:

   ```bash
   OPENROUTER_API_KEY="$(op item get 'OpenRouter API Key' --vault 'Automação' --fields credential --reveal)" \
   python scripts/openrouter_model_recommender.py \
     --eval-language pt-BR --limit 5 --min-throughput 60 \
     --input text,image --tool-calls --structured-outputs --min-context 128000
   ```

2. Se houver menos de dois candidatos, pare; não relaxe requisitos nem invente candidatos.

3. **Pré-flight da suíte:** procure casos executáveis para os quatro gates abaixo. Se algum não existir, crie-o no framework de Eval já adotado pelo repositório antes de testar candidatos. Sem cobertura nos quatro, **pare: nenhum modelo pode ser aprovado**.

   | Gate obrigatório | Critério mínimo |
   |---|---|
   | Idioma nativo (`eval_language`) | prompts, entradas, respostas esperadas e critérios no idioma real da aplicação; não substitua o corpus por tradução automática. |
   | Markdown | respostas com a estrutura exigida (títulos/listas/tabelas/fences aplicáveis) e validação determinística de sintaxe, inclusive fences não fechados. |
   | Tool Calls | chamada controlada do mesmo modelo via `:exacto`; valide escolha da ferramenta, schema e argumentos, resultado e recuperação/abstenção para ferramenta inválida/indisponível. |
   | Antialucinação | casos grounded e sem resposta; afirmações devem vir da evidência; sem evidência, deve declarar incerteza, pedir contexto ou recusar. Reprove fatos, citações, resultados de tool ou detalhes inventados. |
   | Ganho vs. mercado | compare cada candidato no mesmo corpus contra ≥3 baselines atuais, com IDs/versões/providers pinados e de provedores distintos; inclua o modelo de produção atual, se houver. Registre `Δ pass_rate` global e por gate (pontos percentuais), custo, latência e throughput. |

4. Execute cada candidato no reasoning inicial (`xhigh` ou maior suportado; para `max_tokens`, use o mapa local equivalente). Uma combinação `modelo + variante + reasoning` só passa se **cada gate** e a taxa global atingirem `pass_rate >= 95%`, ou o limiar explicitamente configurado pela suíte. Gate ausente ou falho desqualifica o candidato.

   **Prioridade de execução:** dispare em paralelo todas as combinações independentes de `modelo + variante + reasoning` (candidatos e baselines) para economizar tempo. Cada worker usa o mesmo snapshot de corpus/prompts/tools e grava resultado imutável separado. Limite a concorrência por provider conforme rate limits, orçamento e capacidade do runner; retries seguem a mesma política para todos. Só agregue métricas e decida principal/fallback após todos os jobs terminarem; não paralelize etapas dependentes nem compartilhe arquivos mutáveis.

5. Reduza o reasoning por sobrevivente: `xhigh → high → medium → low → minimal`, ignorando níveis não suportados. Ao falhar, retenha o menor nível anterior aprovado.

6. Somente com pelo menos dois modelos distintos aprovados nos quatro gates, o Eval escolhe `principal` e `fallback`: menor custo total observado → menor latência → maior throughput. Aplique runtime manualmente.

7. Revalide em até 30 dias, e quando mudarem idioma, contrato Markdown, ferramentas, corpus/grounding, modelo, provider, preço, reasoning ou suíte.

## Saída

Entregue apenas:

- até cinco candidatos com endpoint, reasoning inicial e throughput;
- o guia de Eval acima.

Não anuncie vencedor antes dos quatro gates aprovados e não altere runtime.
