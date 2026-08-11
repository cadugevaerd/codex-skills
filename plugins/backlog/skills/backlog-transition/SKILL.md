---
name: backlog-transition
description: Transita item entre estados canônicos.
argument-hint: "--db PATH --id ID --status STATE"
user-invocable: true
disable-model-invocation: true
---
# Transição

Após doctor e confirmação, execute `<BACKLOGCTL> --json item transition --db PATH --id ID --status STATE`. Use apenas `open`, `in_progress`, `done`, `cancelled` ou `merged`; `blocked` é condição, não state. `--to` é inválido e resulta em usage/exit 2; um estado que não seja uma transição legal da FSM resulta em erro de domínio/exit 1.

## Contract CLI v2.4.0
Use `item transition --status STATE`; `--to` is unsupported. This is the normal legal FSM, and `merged` remains terminal. `item reconcile-status` é reparo administrativo auditado, não uma transição ordinária.
