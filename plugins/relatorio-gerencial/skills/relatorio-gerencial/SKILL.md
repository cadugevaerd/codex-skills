---
name: relatorio-gerencial
combinando as tarefas atuais informadas manualmente com o backlog técnico exportado exclusivamente pela CLI `backlogctl`. Use quando o usuário pedir report/status gerencial, resumo não técnico do trabalho atual, PDF de detalhes para gerente, consolidação de backlog multi-repo, ou mencionar relatório gerencial.
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

A única fonte é a saída estruturada de `backlogctl --json export consolidated --db PATH`.
O binário (`BACKLOGCTL_BIN`), base (`--db` ou `BACKLOG_DB_PATH`) e timeout
(`--timeout` ou `BACKLOGCTL_TIMEOUT`) são configuráveis. O script valida o envelope
`result=ok` e `data`; erro, comando ausente ou timeout é reportado, sem fallback.
A configuração de repositórios permanece apenas metadado/filtro.

> **Config opcional `~/.claude/relatorio-gerencial.json`.** Guarda preferências e metadados
> de repositórios/filtros; nunca é fonte de itens. Não há modo legado ou fallback.

## Fluxo

1. Receba do usuário as tarefas atuais manualmente. Trate-as como prioridade do report.
2. Garanta que o PATH da base esteja disponível por `--db` ou `BACKLOG_DB_PATH`.
3. Colete via `coletar_backlogs.py`, que chama `backlogctl --json export consolidated --db PATH`. Opcional: `--repo <nome>` para filtrar.
4. Use agentes em paralelo quando disponível: um agente por `repo` para inspecionar e resumir aquele repo. Cada agente retorna JSON normalizado; o agente principal consolida e escreve o PDF.
5. Agrupe microtarefas por resultado de negócio, não por arquivo, módulo ou id técnico.
6. Gere um PDF com primeira página executiva e páginas posteriores detalhando cada item, em linguagem de gerente, com emojis e hierarquia visual.
7. Responda no chat com o caminho do PDF e 3–5 bullets do que entrou no report.

## Scripts

Use os scripts em vez de reimplementar a lógica:

- `scripts/coletar_backlogs.py`: chama `backlogctl --json export consolidated --db PATH`, valida o envelope e normaliza dados estruturados; não lê arquivos de backlog.
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
