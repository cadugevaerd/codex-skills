---
name: backlog-doctor
description: Verifica runtime e integridade sem mutar.
argument-hint: "--db PATH"
user-invocable: true
disable-model-invocation: true
---
# Doctor

Execute `backlogctl [--json] doctor --db PATH`. Opcionalmente verifique `backlogctl --version` antes. Relate stdout, stderr e exit code; doctor não repara nem escreve. Em 2.4.0, DB ausente falha sem ser criado e store atrasado não é migrado: use `store init` ou `update migrate --backup-dir DIR --confirm` conforme o caso. Não invente capabilities nem trate erro de domínio como JSON de sucesso.