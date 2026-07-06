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

## Licenca

MIT para a colecao, conforme o repo de origem. O plugin `code-review-cadu`
preserva tambem a licenca Apache-2.0 do fork do code review oficial.
