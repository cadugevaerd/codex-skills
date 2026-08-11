---
name: backlog
description: Orquestra Backlog v2.1 com preview, fail-closed e confirmação explícita.
argument-hint: "backlog|item|context|decision|format|export|merge|import|todo|update|doctor"
user-invocable: true
disable-model-invocation: false
---
# Orquestrador Backlog

Antes de chamar uma rota, liste: comando exato, backlog/fonte, leitura ou mutação, confirmação e proposal ID/SHA esperado. Verifique caminho, `version` e `doctor`; em dúvida, pare sem fallback.

Superfície: `store`, `doctor`, `backlog`, `item`, `context`, `decision`, `format`, `export`, `merge`, `import`, `todo` e `update`. Toda mutação exige confirmação explícita; proposals/import/scans devem ser revalidados antes de apply.

CLI 2.4.0, DB schema 5, envelope contract 2 e import document contract 3. `doctor` é read-only: DB ausente exige `store init` e store atrasado exige `update migrate --backup-dir DIR --confirm`. Preserve `description`; use `item reconcile-status`/`archive` apenas como operações administrativas confirmadas. Nunca leia SQLite diretamente nem trate JSON v1 como import nativo.
