# Codex Skills

Colecao de Agent Skills para Codex, convertida do marketplace Claude Code
[`cadugevaerd/claude-skills`](https://github.com/cadugevaerd/claude-skills).

Este repo e um marketplace local do Codex. Cada skill continua instalavel como
plugin individual.

| Plugin | O que faz |
| --- | --- |
| `backlog` | Mantém o backlog **GLOBAL** `~/.backlog/backlog.json` como fonte única de trabalho diferido para todos os repositórios. Registra, tria, promove, resolve e descarta itens; `merge` propõe a absorção auditável de duplicatas abertas no mesmo repo, e `consolidado` gera `consolidado_backlog.md` por clusters de negócio e blocos visuais de criticidade, com resumo de prioridade, problema e resolução em linguagem não técnica. |
| `code-review-cadu` | Revisa PRs com veredicto `GO`/`NO-GO` por finding e encaminha itens diferiveis ao backlog apos confirmacao. |
| `code-debug` | Debug por causa raiz: reproduz comando, analisa logs, instrumenta quando necessario e entrega relatorio com causa comprovada e sugestao de fix. |
| `relatorio-gerencial` | Gera relatorios executivos (uma pagina) de tarefas atuais e backlog multi-repositorio com linguagem gerencial e PDF. |
| `grillme-langgraph` | Entrevista tecnica para desenhar um fluxo LangGraph com diagrama, State CRUE, tabela de nodes e fronteiras deterministicas. |
| `grillme-gestor` | Versao sem jargao tecnico da `grillme-langgraph`, voltada a gestores, salvando o artefato tecnico em markdown. |
| `rag-kag-decision` | Decide quando usar RAG, KAG, GraphRAG ou abordagem hibrida conforme documentos, entidades, relacoes, regras, temporalidade, custo e risco. |
| `modelos-custo-beneficio` | Consulta OpenRouter e lista até 5 candidatos para Model Engineering Eval, com reasoning controlável, throughput p75/p50 ≥60 t/s e variantes `:exacto`/`:nitro`; não decide runtime. |
| `facilitador-reunioes` | Cria convites, objetivos claros, pré-briefing, roteiro de condução e próximos passos para reuniões objetivas. |
| `langsmith-evals` | Projeta, executa e audita evals LangSmith-first para chatbots, RAG, agents, nodes e grafos. Inclui Engineer, Pytest Engineer deterministico e Auditor independente, fixados em `gpt-5.6-terra`. |

## Instalacao local

Da raiz deste repo:

```bash
codex plugin marketplace add .
codex plugin add backlog@codex-skills
codex plugin add code-review-cadu@codex-skills
codex plugin add code-debug@codex-skills
codex plugin add relatorio-gerencial@codex-skills
codex plugin add grillme-langgraph@codex-skills
codex plugin add grillme-gestor@codex-skills
codex plugin add rag-kag-decision@codex-skills
codex plugin add modelos-custo-beneficio@codex-skills
codex plugin add facilitador-reunioes@codex-skills
codex plugin add langsmith-evals@codex-skills
```

A skill `/langsmith-evals` fica disponível imediatamente. Para registrar também os
tres custom agents do Codex, execute uma vez a partir do clone deste marketplace:

```bash
python3 plugins/langsmith-evals/scripts/install_codex_agents.py
```

O instalador é idempotente, mantém backup do `config.toml`, fixa
`model = "gpt-5.6-terra"` nos tres agentes e oferece `--uninstall`.

Para listar o catalogo:

```bash
codex plugin list --marketplace codex-skills
```

## Uso do backlog global

```text
/backlog add Corrigir timeout de webhook repo=api-pagamentos
/backlog list repo=api-pagamentos
/backlog consolidado repo=all               # preview e gera ./consolidado_backlog.md após confirmação
/backlog consolidado repo=api-pagamentos output=./consolidado_backlog.md
/backlog format repo=api-pagamentos
/backlog merge repo=api-pagamentos       # proposta/dry-run; confirma antes de gravar
/backlog merge repo=all                  # confirma cada repo separadamente
/backlog merge undo <event_id>           # só se o estado auditado ainda corresponder
```

O `merge` nunca cria IDs: preserva um item canônico aberto já existente e marca de
1 a 3 fontes como `mesclado`, com `merge_history` append-only no schema v3. Itens
mesclados não entram na listagem padrão nem no relatório gerencial.

`/backlog consolidado` é somente leitura da fonte global: agrupa itens `aberto` e
`em-andamento` por objetivo de negócio e criticidade; gera `consolidado_backlog.md` com resumo de prioridade e blocos `Crítica`/`Alta`/`Média`/`Baixa`, além de **Problema** e **O que será resolvido** em linguagem não técnica. O arquivo é um
cache derivado; ele não altera `backlog.json` e pede confirmação antes de substituir
um consolidado existente.

## Estrutura

```text
.agents/plugins/marketplace.json
plugins/
  backlog/
    .codex-plugin/plugin.json
    skills/backlog/SKILL.md
  code-review-cadu/
    .codex-plugin/plugin.json
    skills/code-review-cadu/SKILL.md
  code-debug/
    .codex-plugin/plugin.json
    skills/code-debug/SKILL.md
  relatorio-gerencial/
    .codex-plugin/plugin.json
    skills/relatorio-gerencial/
  grillme-langgraph/
    .codex-plugin/plugin.json
    skills/grillme-langgraph/
  grillme-gestor/
    .codex-plugin/plugin.json
    skills/grillme-gestor/
  rag-kag-decision/
    .codex-plugin/plugin.json
    skills/rag-kag-decision/
  modelos-custo-beneficio/
    .codex-plugin/plugin.json
    skills/modelos-custo-beneficio/
  facilitador-reunioes/
    .codex-plugin/plugin.json
    skills/facilitador-reunioes/
  langsmith-evals/
    .codex-plugin/plugin.json
    agents/*.toml
    scripts/install_codex_agents.py
    skills/langsmith-evals/
```

## Notas da conversao

- Manifestos Claude (`.claude-plugin/plugin.json`) foram convertidos para
  manifestos Codex (`.codex-plugin/plugin.json`).
- O marketplace Claude (`.claude-plugin/marketplace.json`) virou
  `.agents/plugins/marketplace.json`.
- A skill `backlog` usa `AGENTS.md` como arquivo normativo principal no Codex,
  mantendo compatibilidade com `CLAUDE.md` em projetos herdados.
- A skill `code-review-cadu` foi ajustada para falar em revisores/subagentes
  genericos do Codex, sem nomes de modelos Claude.
- A skill `rag-kag-decision` ajuda a escolher RAG, KAG, GraphRAG ou hibrido com base em documentos, entidades, relacoes, regras, temporalidade, custo e risco.
- A skill `modelos-custo-beneficio` consulta OpenRouter em tempo real e entrega candidatos para o Model Engineering Eval local: reasoning controlável, throughput p75/p50 >=60 t/s e variantes `:exacto`/`:nitro`, sem alteração de runtime.
- A skill `facilitador-reunioes` transforma pedidos vagos em convite com objetivo, pré-briefing, pauta, condução e próximos passos com dono/prazo.
- O plugin `langsmith-evals` usa LangSmith como control plane para Dataset, Experiments, Traces e Feedback, preserva pytest/oráculos determinísticos e separa execução (`Engineer`) de aprovação independente (`Auditor`). Como plugins Codex não registram custom roles automaticamente, o instalador gerencia as seções em `~/.codex/config.toml`.

## Licenca

MIT para a colecao, conforme o repo de origem. O plugin `code-review-cadu`
preserva tambem a licenca Apache-2.0 do fork do code review oficial.
