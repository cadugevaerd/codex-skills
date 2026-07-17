---
name: "langsmith-evals"
description: "Especialista LangSmith-first para projetar, implementar, executar e auditar evals de chatbots, RAG, agentes, nodes e grafos; criar Pytest deterministico, datasets/evaluators/experiments/backtests; comparar modelos e aplicar gates com evidencia. Use em mudancas de modelo, prompt, tool, retrieval, contrato, LangGraph ou comportamento agentico que precisem de qualidade mensuravel."
argument-hint: "<sistema ou mudanca a avaliar; opcional: engineer|pytest|audit>"
---

# LangSmith Evals

## Missao

Transformar requisitos de comportamento em evidencias reproduziveis. O LangSmith e o **control plane** de evals agenticos: Dataset, Examples, Experiments, Traces e Feedback. O repositorio continua contendo codigo, pytest, fixtures de bootstrap e oraculos deterministicos.

## Roteamento

- **Engineer**: desenhar ou alterar dataset/evaluators, instrumentar target, executar experiments, backtests e implementar gates.
- **Pytest Engineer**: implementar por TDD somente oraculos deterministicos, contratos e isolamento de side effects; nao julga semantica nem aprova promocao.
- **Auditor**: revisar evidencias existentes e emitir `GO`, `NO-GO` ou `BLOCKED`; nao corrigir a propria evidencia.
- No Codex, prefira os custom agents `langsmith_evals_engineer`, `langsmith_pytest_engineer` e `langsmith_evals_auditor` quando instalados.

A separacao e intencional: quem escolhe rubricas e implementa o target nao deve ser o unico aprovador da promocao.

## Contrato nao negociavel

1. Todo eval que execute LLM, node agentico, trajetoria ou grafo MUST produzir um LangSmith Experiment real.
2. Tracing isolado, stdout, screenshot ou JSON local nao equivalem a Experiment.
3. Numeros, schema, DAX/SQL, argumentos de tool, artefatos, seguranca e invariantes usam oraculos deterministicos; LLM-as-judge avalia apenas criterios semanticos.
4. Baseline e candidato usam o mesmo Dataset, split, evaluators e condicoes comparaveis.
5. Outputs historicos nao sao automaticamente ground truth. Use referencia validada, avaliador sem referencia ou revisao humana.
6. Evals nao podem causar side effects reais. Use adapters fake, sandbox, dry-run, mocks contratuais ou test mode explicitamente verificado.
7. Nenhum resultado e inventado. Sem credencial/rede/evidencia: `BLOCKED`, nunca PASS ou SKIP silencioso.
8. Casos criticos sao gates individuais; media agregada nao pode esconder regressao critica.
9. Segredos e PII nao entram em dataset, metadata, trace ou prompt do judge sem sanitizacao e politica aprovada.

## Fluxo obrigatorio do Pytest Engineer

1. Classificar cada criterio como mecanicamente verificavel ou semantico; recusar usar judge para o primeiro e encaminhar o segundo ao Engineer.
2. Definir input, output, invariantes, tolerancias, edge cases e isolamento antes de editar.
3. Trabalhar por TDD: executar a falha inicial esperada, implementar a mudanca minima e rodar teste focal, modulo e suite relevante.
4. Controlar rede, LLM, filesystem, clock, UUID, random e gateways com fixtures/fakes; nenhum side effect real e permitido.
5. Usar `@pytest.mark.langsmith` apenas quando a publicacao de evidencia for parte do eval; a assercao Pytest continua sendo o oraculo.
6. Entregar comandos e outputs reais, contagens, failures, arquivos alterados e limitacoes; nao emitir decisao de promocao.

Leia `references/pytest-deterministic.md` para o catalogo de oraculos, exemplos e anti-padroes.

## Fluxo obrigatorio do Engineer

### 1. Descobrir o sistema

Leia constituicao/AGENTS/CLAUDE, codigo do target, State, tools, testes, tracing, config e evals existentes. Reaproveite harness valido; nao crie runner paralelo sem necessidade comprovada.

Classifique o target:

| Target | O que medir |
|---|---|
| Chatbot | resposta final, aderencia, seguranca |
| RAG | retrieval, relevancia, groundedness, resposta |
| Agent/ReAct | resposta, tool calls, trajetoria, side effects |
| LangGraph node | transformacao de State e contrato do node |
| Grafo completo | outcome, trajetoria, custo, latencia, robustez |

### 2. Escrever o eval contract

Antes do codigo, registre:

- comportamento e risco da mudanca;
- unidade de avaliacao: response, retrieval, step/node, trajectory ou graph;
- segmentos e casos criticos;
- dataset/split/version;
- baseline e candidatos;
- evaluators, rubricas e thresholds;
- metadata obrigatoria;
- regra de promocao e rollback.

Se o criterio nao puder ser transformado em exemplo, evaluator ou gate, ele ainda nao e criterio de aceite.

### 3. Construir o Dataset

Inclua happy paths, edge cases, regressions, adversarial/safety e casos reais sanitizados. Use splits como `smoke`, `regression`, `critical`, `adversarial` e `production-backtest` quando fizer sentido.

Cada Example deve ter input minimo, reference output somente quando confiavel e metadata para segmentacao. Versione semanticamente por metadata/manifest e registre a origem dos casos.

### 4. Implementar evaluators

Ordem de preferencia:

1. **deterministico**: igualdade/tolerancia, schema, regex, AST, parser, tool args, invariantes e ausencia de side effects;
2. **heuristico**: regras explicitas e auditaveis;
3. **LLM-as-judge**: somente semantica, com rubric atomica, structured output e evidencias citadas;
4. **humano**: ambiguidade de dominio, calibracao e casos de alto risco.

Um evaluator retorna nome estavel, score/label e comentario util. Nao combine criterios independentes em uma unica nota opaca. Calibre judges contra exemplos rotulados e teste vies de ordem, verbosidade, self-preference e prompt injection.

### 5. Instrumentar o target

O target deve aceitar o formato do Example e retornar output avaliavel. Para nodes/grafos, capture estado relevante e trajetoria sem acoplar o evaluator a detalhes irrelevantes. Em test mode, substitua ferramentas destrutivas e prove que nenhum side effect real ocorreu.

### 6. Executar Experiment

Use `evaluate`/`aevaluate`; registre `experiment_prefix`, descricao e metadata. No minimo:

- `git_sha`, branch e versao do runtime;
- modelo, provider e parametros;
- reasoning effort/budget;
- versao de prompt, tools e graph;
- dataset, split e versao;
- baseline/candidate e motivo da mudanca.

Guarde URL/ID do Dataset e Experiment. O relatorio local e apenas exportacao derivada.

### 7. Comparar e decidir

Compare por evaluator e segmento, nao apenas pela media. Relate qualidade, custo, latencia, tokens, erros e incerteza. Para mudancas de modelo, prompt, tools ou graph, execute baseline e candidatos pareados.

Gate recomendado:

```text
GO = todos os casos critical passam
  AND nenhum contrato deterministico regride
  AND thresholds semanticos passam
  AND custo/latencia ficam dentro do budget
  AND side effects permanecem isolados
```

### 8. Backtest e producao

Para sistemas em producao, converta traces representativos sanitizados em Dataset e rode o candidato offline. Nao use output historico como verdade por padrao. Depois da promocao, configure online evaluators/amostragem e alertas para drift, erros, custo, latencia e regressao por segmento.

### 9. Verificar

Rode testes locais, execute o Experiment e leia o resultado real. A entrega deve conter comandos executados, IDs/URLs, scores segmentados, failures, decisao e limitacoes.

## Fluxo obrigatorio do Auditor

1. Confirmar identidade e versionamento do Dataset/Experiment.
2. Verificar comparabilidade baseline-candidato e metadata.
3. Revisar adequacao dos evaluators e calibracao do judge.
4. Inspecionar failures e casos criticos, nao somente agregados.
5. Verificar isolamento de side effects e ausencia de leakage/PII.
6. Validar thresholds contra config/constituicao, sem inventar criterio retroativo.
7. Emitir:
   - `GO`: evidencia completa e gates aprovados;
   - `NO-GO`: evidencia real mostra regressao/violacao;
   - `BLOCKED`: evidencia ausente, incomparavel ou inacessivel.

## Formato de saida

```markdown
# LangSmith Eval Report

## Decisao
GO | NO-GO | BLOCKED

## Escopo
- Target:
- Mudanca:
- Dataset/split/version:
- Baseline Experiment:
- Candidate Experiment:

## Evidencias
| Evidencia | ID/URL/comando | Resultado |
|---|---|---|

## Resultados por gate
| Gate | Baseline | Candidate | Threshold | Status |
|---|---:|---:|---:|---|

## Casos criticos e regressions
- ...

## Custo, latencia e confiabilidade
- ...

## Findings / acoes
1. ...
```

## Referencias do plugin

Leia `references/patterns.md` para exemplos de implementacao, `references/pytest-deterministic.md` para testes mecanicos e `references/audit-checklist.md` para criterios de promocao e links oficiais. Consulte a documentacao oficial atual antes de assumir assinatura de SDK.
