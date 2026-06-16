---
name: relatorio-gerencial
description: Gera um PDF executivo de uma pagina, visualmente agradavel e com emojis, para enviar ao gerente com tarefas atuais informadas manualmente e backlog coletado de varios repositorios. Use quando o usuario pedir report/status gerencial, resumo nao tecnico de trabalho atual, PDF para gerente, consolidacao de backlog multi-repo, adicionar/remover repositorios gerenciados, ou mencionar relatorio gerencial.
---

# Relatorio Gerencial

Use esta skill para transformar tarefas atuais e backlog tecnico em um report executivo, nao tecnico, de no maximo uma pagina.

## Fonte de Verdade

Use `~/.claude/relatorio-gerencial.json` como configuracao global dos repositorios. Na primeira chamada da skill, se esse arquivo nao existir, crie automaticamente com:

```bash
python3 scripts/relatorio_config.py init
```

O plugin tambem versiona `assets/relatorio-gerencial.example.json` como exemplo de schema. Nao trate esse arquivo como configuracao viva; ele serve para documentar o formato esperado e facilitar revisao no repo.

Repos padrao:

- `masterai-agents-backend`: `/home/caraujo/projetos/masterai-agents-backend`
- `librechat-private`: `/home/caraujo/projetos/librechat-private`
- `master-agents`: `/home/caraujo/projetos/master-agents`
- `proxy-cm-ai`: `/home/caraujo/projetos/proxy-cm-ai`

Gerencie repositorios com:

```bash
python3 scripts/relatorio_config.py add --name novo-repo --path /caminho/absoluto
python3 scripts/relatorio_config.py remove --name novo-repo
python3 scripts/relatorio_config.py disable --name proxy-cm-ai
python3 scripts/relatorio_config.py enable --name proxy-cm-ai
python3 scripts/relatorio_config.py list
```

## Fluxo

1. Receba do usuario as tarefas atuais manualmente. Trate-as como prioridade do report.
2. Garanta que a configuracao global exista; na primeira execucao, rode `scripts/relatorio_config.py init` sem pedir confirmacao.
3. Aplique pedidos de adicionar, remover, habilitar ou desabilitar repositorios antes de gerar o report.
4. Colete `.specify/backlog.json` de todos os repositorios habilitados.
5. Use agentes em paralelo quando disponivel: um agente por repositorio para inspecionar e resumir o backlog daquele repo. Cada agente deve retornar JSON normalizado; o agente principal consolida e escreve o PDF.
6. Agrupe microtarefas por resultado de negocio, nao por arquivo, modulo ou id tecnico.
7. Gere um PDF de uma pagina com linguagem de gerente, emojis e hierarquia visual.
8. Responda no chat com o caminho do PDF e 3-5 bullets do que entrou no report.

## Scripts

Use os scripts em vez de reimplementar a logica:

- `scripts/relatorio_config.py`: cria/lista/adiciona/remove/habilita/desabilita repositorios no JSON global.
- `scripts/coletar_backlogs.py`: coleta e normaliza backlogs dos repos habilitados.
- `scripts/agrupar_tasks.py`: combina tarefas manuais e backlog, unindo microtarefas em iniciativas maiores.
- `scripts/render_pdf.py`: gera HTML e PDF de uma pagina usando Playwright, WeasyPrint ou Chromium headless quando disponivel.

Exemplo de execucao:

```bash
python3 scripts/coletar_backlogs.py --out /tmp/backlogs.json
python3 scripts/agrupar_tasks.py --backlogs /tmp/backlogs.json --manual-tasks /tmp/tasks-atuais.txt --out /tmp/relatorio-dados.json
python3 scripts/render_pdf.py --input /tmp/relatorio-dados.json --out ./relatorio-gerencial.pdf
```

## Agrupamento

Agrupe itens pequenos em ate 5 iniciativas maiores. Prefira titulos como:

- "Estabilizar o fluxo de atendimento"
- "Reduzir riscos antes da proxima entrega"
- "Melhorar confiabilidade das integracoes"
- "Aumentar visibilidade e controle operacional"
- "Diminuir divida tecnica acumulada"

Cada iniciativa deve ter: titulo, emoji, explicacao curta, repos afetados, urgencia, proxima acao e quantidade de microtarefas incluidas.

## Saida

O PDF deve caber em uma pagina. Use secoes:

- 🎯 Foco Atual
- ⚠️ Riscos e Atencoes
- 🚧 Proximos Blocos
- ✅ Decisoes Necessarias

Evite jargao tecnico, stack traces, nomes de arquivos, ids de backlog como texto principal e listas longas. Se houver informacao demais, priorize tarefas atuais, riscos altos e no maximo 5 grupos.
