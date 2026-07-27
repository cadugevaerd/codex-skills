---
name: backlog-export
description: Exporta formato derivado suportado sem mutar fonte.
argument-hint: "--db PATH --code CODE"
user-invocable: true
disable-model-invocation: false
---
# Exportar

Após doctor, execute `backlogctl [--json] export json|markdown|consolidated --db PATH [--code CODE]`. `--db` pertence ao comando export. Não alegue arquivo salvo sem verificar o destino. Consolidated deve conter `data.backlogs[]` com `items[]` aninhados e sem `data.items`.