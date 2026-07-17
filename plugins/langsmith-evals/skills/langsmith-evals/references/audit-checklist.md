# Checklist de auditoria e fontes oficiais

## Dataset

- [ ] ID/nome, descricao, owner e versao identificados.
- [ ] Splits e metadata permitem segmentar critical/regression/adversarial.
- [ ] Casos representam uso real e riscos, sem PII/segredos indevidos.
- [ ] References tem provenance e revisao; outputs historicos nao foram promovidos a verdade automaticamente.
- [ ] Processo de update e reconciliacao evita duplicatas e drift silencioso.

## Target e isolamento

- [ ] Target do Experiment corresponde ao codigo/commit declarado.
- [ ] Node/graph recebe State/inputs validos e retorna output avaliavel.
- [ ] Tools destrutivas usam fake/sandbox/dry-run verificavel.
- [ ] Erros, retries e timeouts permanecem na analise.

## Evaluators

- [ ] Criterios objetivos usam oraculos deterministicos.
- [ ] Cada judge tem uma rubrica atomica e structured output.
- [ ] Judge foi calibrado contra labels humanos/fixtures representativos.
- [ ] Prompt injection, position bias, verbosity bias e self-preference foram considerados.
- [ ] Score inclui comentario/evidencia suficiente para diagnostico.

## Experiments

- [ ] Baseline e candidato usam mesmo Dataset, split e evaluator set.
- [ ] Metadata inclui git SHA, modelo/provider/parametros, prompt/tools/graph e dataset version.
- [ ] Ha ID/URL verificavel e resultados nao foram fabricados/exportados sem origem.
- [ ] Comparacao mostra segmentos, casos criticos, custo, latencia, tokens e erros.
- [ ] Amostra e variancia sustentam o nivel de certeza declarado.

## Promotion gate

- [ ] Thresholds foram definidos antes da decisao ou justificados explicitamente.
- [ ] Nenhum critical falhou.
- [ ] Nenhum contrato deterministico ou safety gate regrediu.
- [ ] Quality/cost/latency respeitam budget.
- [ ] Rollback e monitoramento online estao definidos.

## Veredicto

- **GO**: todos os itens obrigatorios tem evidencia e os gates passam.
- **NO-GO**: evidencias reais mostram falha/regressao.
- **BLOCKED**: Dataset/Experiment/metadata/evidencia ausente ou incomparavel.

## Documentacao oficial

Use estas fontes como autoridade e confira a versao atual:

- Evaluation overview: https://docs.langchain.com/langsmith/evaluation
- Evaluate an LLM application: https://docs.langchain.com/langsmith/evaluate-llm-application
- Evaluate a graph: https://docs.langchain.com/langsmith/evaluate-graph
- Evaluate a complex agent: https://docs.langchain.com/langsmith/evaluate-complex-agent
- RAG evaluation: https://docs.langchain.com/langsmith/evaluate-rag-tutorial
- Test ReAct agents with pytest: https://docs.langchain.com/langsmith/test-react-agent-pytest
- Backtest a new agent: https://docs.langchain.com/langsmith/run-backtests-new-agent
- Datasets: https://docs.langchain.com/langsmith/manage-datasets
- Evaluators: https://docs.langchain.com/langsmith/evaluation-concepts
- Experiments: https://docs.langchain.com/langsmith/compare-experiment-results
- Online evaluation: https://docs.langchain.com/langsmith/online-evaluations
- Observability/tracing: https://docs.langchain.com/langsmith/observability

## Fontes oficiais dos agentes

- Codex multi-agent/custom roles: https://developers.openai.com/codex/multi-agent/
- Codex plugins: https://developers.openai.com/codex/plugins/
- Claude Code subagents: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- Claude Code plugins: https://docs.anthropic.com/en/docs/claude-code/plugins
