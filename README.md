# Codex Skills

Colecao de Agent Skills para Codex, convertida do marketplace Claude Code
[`cadugevaerd/claude-skills`](https://github.com/cadugevaerd/claude-skills).

Este repo e um marketplace local do Codex. Cada skill continua instalavel como
plugin individual.

| Plugin | O que faz |
| --- | --- |
| `backlog` | Mantem `.specify/backlog.json` como fonte da verdade de itens diferidos, com bootstrap de `BACKLOG.md` e instrucoes para agentes. A operacao `format` re-tria a severidade (4 niveis) e atribui o rank 1-100 (ordem de ataque). |
| `code-review-cadu` | Revisa PRs com veredicto `GO`/`NO-GO` por finding e encaminha itens diferiveis ao backlog apos confirmacao. |
| `code-debug` | Debug por causa raiz: reproduz comando, analisa logs, instrumenta quando necessario e entrega relatorio com causa comprovada e sugestao de fix. |
| `relatorio-gerencial` | Gera relatorios executivos (uma pagina) de tarefas atuais e backlog multi-repositorio com linguagem gerencial e PDF. |
| `grillme-langgraph` | Entrevista tecnica para desenhar um fluxo LangGraph com diagrama, State CRUE, tabela de nodes e fronteiras deterministicas. |
| `grillme-gestor` | Versao sem jargao tecnico da `grillme-langgraph`, voltada a gestores, salvando o artefato tecnico em markdown. |
| `rag-kag-decision` | Decide quando usar RAG, KAG, GraphRAG ou abordagem hibrida conforme documentos, entidades, relacoes, regras, temporalidade, custo e risco. |
| `modelos-custo-beneficio` | Consulta OpenRouter em tempo real e recomenda 5 modelos LLM latest por custo-beneficio, filtrando throughput minimo, input modalities, Tool Calls, structured outputs, contexto e custo. |
| `facilitador-reunioes` | Cria convites, objetivos claros, pré-briefing, roteiro de condução e próximos passos para reuniões objetivas. |

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
```

Para listar o catalogo:

```bash
codex plugin list --marketplace codex-skills
```

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
- A skill `modelos-custo-beneficio` consulta OpenRouter em tempo real e aceita requisitos via parametro (`throughput_min`, `input`, `tool_calls`, `structured_outputs`, `min_context`, `max_cost_per_1m`).
- A skill `facilitador-reunioes` transforma pedidos vagos em convite com objetivo, pré-briefing, pauta, condução e próximos passos com dono/prazo.

## Licenca

MIT para a colecao, conforme o repo de origem. O plugin `code-review-cadu`
preserva tambem a licenca Apache-2.0 do fork do code review oficial.
