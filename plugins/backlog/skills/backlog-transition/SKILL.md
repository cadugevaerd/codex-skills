---
name: backlog-transition
description: Transita item entre estados canônicos.
argument-hint: "--db PATH --id ID --to STATE"
user-invocable: true
disable-model-invocation: true
---
# Transição

Após doctor e confirmação, execute `backlogctl [--json] item transition --db PATH --id ID --to STATE`. Use apenas `open`, `in_progress`, `done`, `cancelled` ou `merged`; `blocked` é condição, não state. Reporte stderr/exit 1 em transição inválida.