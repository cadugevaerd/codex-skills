---
name: backlog-todo
description: Escaneia TODO/FIXME software-only e aplica somente com opt-in, hash e confirmação.
argument-hint: "scan|apply --db PATH --code ABC --path SOURCE --expected-sha256 SHA"
user-invocable: true
disable-model-invocation: true
---
# TODO/FIXME

Rota opt-in explícita e apenas para profile `software`. Resuma backlog, path autorizado, efeito e confirmação.

`<BACKLOGCTL> --json todo scan --db PATH --code ABC --path SOURCE` é puro. Só após confirmação execute `<BACKLOGCTL> --json todo apply --db PATH --code ABC --path SOURCE --expected-sha256 SHA --confirm`. Nunca execute os TODOs nem altere arquivos-fonte.
