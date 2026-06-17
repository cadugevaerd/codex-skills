---
name: relatorio-gerencial
description: Gera um PDF executivo (resumo + páginas de detalhe, visual e com emojis) para enviar ao gerente, combinando as tarefas atuais informadas manualmente com o backlog técnico coletado do backlog GLOBAL (~/.backlog/backlog.json) — todos os repositórios de uma vez, agrupados pelo campo `repo`. Use quando o usuário pedir report/status gerencial, resumo não técnico do trabalho atual, PDF de detalhes para gerente, consolidação de backlog multi-repo, ou mencionar relatório gerencial.
metadata:
  author: "civilmaster"
  source: "originada no codex-skills; portada para o claude-skills; consome o backlog global ~/.backlog/backlog.json"
user-invocable: true
disable-model-invocation: false
---

# Relatorio Gerencial

Transforma tarefas atuais + backlog técnico em um report executivo, não técnico,
com primeira página de resumo e páginas posteriores de detalhamento.

## Fonte de Verdade

O backlog é coletado do **backlog GLOBAL único `~/.backlog/backlog.json`** (a mesma
fonte da skill `/backlog`). Os repositórios e itens são **descobertos
automaticamente** — cada item carrega o campo `repo` (repositório-alvo), então o
report cobre todos os repos de uma vez **sem precisar registrar/habilitar nada**.

- `scripts/coletar_backlogs.py` lê o global por padrão, filtra `resolvido`/
  `descartado` e agrupa por `repo`. Para um report de um repo só, use
  `--repo <nome>` (pode repetir).
- Se `~/.backlog/backlog.json` não existir, a skill `/backlog` faz o bootstrap
  dele (ou rode `/backlog init`).

> **Config opcional `~/.claude/relatorio-gerencial.json`.** Guarda só preferências
> do report (idioma, público, `max_groups`). Os comandos de gerenciar repositórios
> (`relatorio_config.py add/remove/enable/disable/list`) e o flag
> `coletar_backlogs.py --no-global` são **legado** — só afetam o modo fallback
> per-projeto (`.specify/backlog.json`), mantido para repos que ainda não estão no
> global. No fluxo normal você **não** precisa deles.

## Fluxo

1. Receba do usuário as tarefas atuais manualmente. Trate-as como prioridade do report.
2. Garanta que `~/.backlog/backlog.json` existe (senão, `/backlog init`).
3. Colete o backlog global de uma vez (`coletar_backlogs.py` — todos os repos, campo `repo` por item). Opcional: `--repo <nome>` para escopar.
4. Use agentes em paralelo quando disponível: um agente por `repo` para inspecionar e resumir aquele repo. Cada agente retorna JSON normalizado; o agente principal consolida e escreve o PDF.
5. Agrupe microtarefas por resultado de negócio, não por arquivo, módulo ou id técnico.
6. Gere um PDF com primeira página executiva e páginas posteriores detalhando cada item, em linguagem de gerente, com emojis e hierarquia visual.
7. Responda no chat com o caminho do PDF e 3–5 bullets do que entrou no report.

## Scripts

Use os scripts em vez de reimplementar a lógica:

- `scripts/coletar_backlogs.py`: coleta e normaliza o backlog **global** (agrupado por `repo`). `--repo` filtra; `--no-global` cai no modo legado per-projeto.
- `scripts/agrupar_tasks.py`: combina tarefas manuais e backlog, unindo microtarefas em iniciativas maiores.
- `scripts/render_pdf.py`: gera HTML e PDF multipágina via Playwright, WeasyPrint, Chromium headless ou Pillow (o que estiver disponível).
- `scripts/relatorio_config.py`: **legado/opcional** — só preferências do report e a config de repos do modo fallback.

Exemplo de execução:

```bash
python3 scripts/coletar_backlogs.py --out /tmp/backlogs.json
python3 scripts/agrupar_tasks.py --backlogs /tmp/backlogs.json --task "Subir agente comercial em dev" --out /tmp/relatorio-dados.json
python3 scripts/render_pdf.py --input /tmp/relatorio-dados.json --out ./relatorio-gerencial.pdf
```

## Agrupamento

Agrupe itens pequenos em até 5 iniciativas maiores. Prefira títulos como:

- "Estabilizar o fluxo de atendimento"
- "Reduzir riscos antes da próxima entrega"
- "Melhorar confiabilidade das integrações"
- "Aumentar visibilidade e controle operacional"
- "Diminuir dívida técnica acumulada"

Cada iniciativa deve ter: título, emoji, explicação curta, repos afetados,
urgência, próxima ação e quantidade de microtarefas incluídas.

## Saida

A primeira página do PDF é um resumo executivo. As páginas seguintes detalham os
itens de backlog agrupados. Use seções:

- 🎯 Foco Atual
- ⚠️ Riscos e Atenções
- 🚧 Próximos Blocos
- ✅ Decisões Necessárias

Evite jargão técnico, stack traces, nomes de arquivos, ids de backlog como texto
principal e listas longas. Se houver informação demais, priorize tarefas atuais e
riscos altos no resumo; mantenha o detalhamento nas páginas posteriores.
