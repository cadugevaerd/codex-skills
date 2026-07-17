---
name: "agentcore-cli"
description: "Opera o Amazon Bedrock AgentCore CLI para criar, desenvolver, validar, implantar, observar e avaliar agentes. Use para AgentCore Runtime, AgentCore CLI, agentcore create/dev/deploy/invoke, CloudWatch traces/logs, evaluators, LLM-as-a-Judge, eval on-demand, batch evaluation, datasets, ground truth, online evals, quality gates e recomendacoes de prompt/tool description."
argument-hint: "<objetivo do agente, operação, ou estratégia de EVAL>"
---

# AgentCore CLI — Runtime, observabilidade e EVALs

Use esta skill para trabalho no **Amazon Bedrock AgentCore** através do CLI oficial `@aws/agentcore`. Ela cobre criação e operação de Runtime e também EVALs comportamentais. EVAL não substitui testes unitários/integrados: mede a qualidade da interação do agente, seus traces e chamadas de tools.

## Princípios não negociáveis

- Antes de operar, confirme CLI, identidade AWS, região, acesso ao modelo e diretório do projeto com evidência real.
- Nunca faça `agentcore deploy`, `agentcore remove all` ou altere recursos AWS sem aprovação explícita do usuário após apresentar `agentcore deploy --dry-run` ou `--diff`.
- Trate credenciais/API keys como segredos: use `agentcore/.env.local` gitignored ou um mecanismo AWS adequado; nunca grave valores em `agentcore.json`, Markdown, commits ou logs.
- Não chame um EVAL de “teste passou” só porque o job terminou. Informe o evaluator, corpus/recorte, ground truth, score agregado, distribuição, custo e threshold.
- Para regras determinísticas (schema, PII, latência, tool obrigatória), prefira ground truth e/ou evaluator code-based (Lambda). LLM-as-a-Judge complementa, não substitui, essas verificações.

## Descoberta e pré-checks

Execute e reporte o resultado antes de uma operação:

```bash
agentcore --help
node --version
uv --version
aws sts get-caller-identity
aws configure get region
```

No projeto, inspecione e valide antes de editar ou implantar:

```bash
agentcore validate
agentcore status --json
```

Para criar um projeto, confirme framework, provider/modelo, protocolo, build, memória e região. Exemplo para LangGraph:

```bash
agentcore create \
  --name MyAgent \
  --framework LangChain_LangGraph \
  --model-provider Bedrock \
  --protocol HTTP \
  --memory none
```

## Desenvolvimento e deploy seguro

```text
create → inspecionar config/código → dev local → invoke/trace → validate
       → deploy --dry-run ou --diff → aprovação explícita → deploy → status/invoke/logs
```

1. Rode o servidor local rastreado e capture logs:
   ```bash
   agentcore dev --logs
   ```
   Se `8080` estiver ocupado, use `agentcore dev -p 3000`; não encerre processo desconhecido.
2. Faça uma invocação representativa e registre entrada, saída, tools e erro, se houver.
3. Antes de deploy, execute:
   ```bash
   agentcore validate
   agentcore deploy --dry-run --json
   # ou: agentcore deploy --diff
   ```
4. Somente após aprovação explícita:
   ```bash
   agentcore deploy -y
   agentcore status --json
   agentcore invoke --runtime MyAgent "<cenario representativo>" --stream
   agentcore logs --runtime MyAgent
   agentcore traces list --runtime MyAgent --limit 10
   ```

AgentCore Runtime executa em ARM64. Para build `Container`, valide dependências e imagem ARM64; `CodeZip` é o padrão simples quando não há dependências de sistema.

## Modelo de EVAL

```text
Cenários / sessões / traces
             │
             ├─ ground truth (quando há resposta, regra ou trajetória esperada)
             ▼
Evaluator ───┬─ Builtin.*
             ├─ LLM-as-a-Judge (rubrica + modelo)
             └─ code-based (Lambda determinística)
             ▼
Score por session / trace / tool call + agregados + evidência para decisão
```

### Níveis de avaliação

| Nível | Avalia | Use para |
|---|---|---|
| `SESSION` | conversa completa | sucesso do objetivo e qualidade fim a fim |
| `TRACE` | um turno/resposta | precisão e completude por resposta |
| `TOOL_CALL` | seleção/uso de tool | ferramenta correta, parâmetros e sequência |

Scores são normalizados de `0` (pior) a `1` (melhor). A escala e o threshold precisam ser definidos antes de comparar versões.

### Evaluators disponíveis

Use built-ins quando encaixarem no critério:

```text
Builtin.Correctness
Builtin.Helpfulness
Builtin.Faithfulness
Builtin.GoalSuccessRate
Builtin.ToolSelectionAccuracy
Builtin.TrajectoryExactOrderMatch
```

Para um avaliador LLM-as-a-Judge customizado, defina rubrica explícita, nível e escala:

```bash
agentcore add evaluator \
  --name ResponseQuality \
  --level TRACE \
  --model us.anthropic.claude-sonnet-4-5-20250514-v1:0 \
  --instructions "Avalie precisão, completude e aderência. Contexto: {context}. Resposta: {assistant_turn}" \
  --rating-scale 1-5-quality
```

Placeholders válidos devem corresponder ao nível:

| Placeholder | Níveis |
|---|---|
| `{context}` | `SESSION`, `TRACE`, `TOOL_CALL` |
| `{assistant_turn}` | `TRACE` |
| `{available_tools}` | `SESSION`, `TOOL_CALL` |
| `{tool_turn}` | `TOOL_CALL` |

Para controle determinístico, registre uma Lambda existente:

```bash
agentcore add evaluator \
  --name SchemaAndSafety \
  --type code-based \
  --level TRACE \
  --lambda-arn arn:aws:lambda:REGION:ACCOUNT:function:SchemaAndSafety \
  --timeout 60
```

## Escolha do modo de EVAL

| Modo | Fonte | Pergunta que responde |
|---|---|---|
| On-demand | traces/sessões históricas | “O que ocorreu no tráfego recente?” |
| Batch | muitas sessões CloudWatch | “A qualidade agregada mudou?” |
| Dataset-driven batch | casos versionados que invocam o runtime | “Esta mudança regrediu cenários críticos?” |
| Online | amostra contínua do tráfego produtivo | “A produção está degradando?” |

### On-demand: investigação orientada por trace

```bash
agentcore run eval \
  --runtime MyAgent \
  --evaluator ResponseQuality Builtin.Faithfulness \
  --days 7 \
  --json
```

Restrinja quando necessário:

```bash
agentcore run eval \
  --runtime MyAgent \
  --evaluator Builtin.Helpfulness \
  --session-id SESSION_ID \
  --days 7
```

Traces podem levar 5–10 minutos para aparecer. Se não houver sessão, aguarde ou aumente `--days`; não conclua que o agente não gerou traces sem investigar observabilidade e região.

### Batch com ground truth: regressão em escala

```bash
agentcore run batch-evaluation \
  --runtime MyAgent \
  --evaluator Builtin.Correctness Builtin.GoalSuccessRate \
  --lookback-days 3 \
  --ground-truth ./ground_truth.json \
  --json
```

Use o formato em `references/ground-truth.example.json` como ponto de partida. Inclua apenas evidências objetivas relevantes:

- `assertions` para objetivo/regra de sucesso;
- `expectedTrajectory.toolNames` para ordem de tools;
- `turns[].expectedResponse.text` para resposta esperada.

### Batch orientado por dataset: gate de release recomendado

Crie/cure um dataset com cenários críticos, edge cases, negativas e regressões já encontradas. Versione-o antes do gate:

```bash
agentcore add dataset --name RegressionSuite
agentcore dataset publish-version --name RegressionSuite --json
agentcore run batch-evaluation \
  --runtime MyAgent \
  --evaluator Builtin.Correctness Builtin.GoalSuccessRate Builtin.ToolSelectionAccuracy \
  --dataset RegressionSuite \
  --dataset-version 1 \
  --json
```

O número de sessões avaliadas deve coincidir com o número de cenários do dataset. Compare candidato e baseline no **mesmo** dataset, modelo de evaluator, rubrica, região, configuração e política de retries.

### Online EVAL: monitoramento de produção

```bash
agentcore add online-eval \
  --name ProductionQuality \
  --runtime MyAgent \
  --evaluator Builtin.Faithfulness ResponseQuality \
  --sampling-rate 5 \
  --enable-on-create

# requer aprovação explícita, pois cria/altera recurso AWS
agentcore deploy
```

| Amostragem | Uso típico |
|---:|---|
| 1–5% | produção com controle de custo |
| 10–25% | staging / validação intensa |
| 100% | teste curto, controlado e com orçamento aprovado |

Monitore e controle o custo:

```bash
agentcore logs evals --runtime MyAgent --since 1h --json
agentcore evals history --runtime MyAgent --json --limit 10
agentcore pause online-eval ProductionQuality
agentcore resume online-eval ProductionQuality
```

## Quality gate em CI/CD

Use EVAL batch dataset-driven em staging; não execute EVAL de produção como precondição de merge. O gate deve falhar para score abaixo do limite **ou** quando houver resultado/contagem ausente.

```bash
set -euo pipefail
result="$(agentcore run batch-evaluation \
  --runtime MyAgent \
  --evaluator Builtin.Correctness Builtin.GoalSuccessRate \
  --dataset RegressionSuite \
  --dataset-version 1 \
  --json)"

printf '%s' "$result" > agentcore-eval-result.json
# Extraia scores/cobertura conforme o schema retornado pela versão instalada e
# falhe fechado se evaluator, média ou número de cenários estiver ausente.
```

Antes de institucionalizar o gate, execute uma baseline aprovada e registre: versão do dataset, commit/configuração do agente, evaluators/modelos/rubricas, thresholds, cobertura, custo, latência e scores por evaluator. Um score agregado aceitável não compensa falha de segurança, trajetória de tool obrigatória ou cenário crítico individual.

## Resultado obrigatório ao usuário

Responda de forma curta e baseada em evidência:

```markdown
## AgentCore / EVAL
- Objetivo e ambiente: runtime, região, commit/configuração.
- Ação executada: comandos reais e status.
- Corpus: traces/sessões ou dataset+versão; cobertura esperada vs concluída.
- Evaluators: nome, tipo, nível, modelo/rubrica ou Lambda.
- Resultado: score por evaluator, threshold, distribuição/falhas críticas e custo/latência quando disponível.
- Decisão: aprovar, bloquear ou investigar — com motivo objetivo.
- Próximo passo: uma ação concreta, ou bloqueio comprovado.
```

## Referências primárias

- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html
- https://github.com/aws/agentcore-cli/blob/main/docs/evals.md
- https://github.com/aws/agentcore-cli/blob/main/docs/batch-evaluation.md
- https://github.com/aws/agentcore-cli/blob/main/docs/commands.md
