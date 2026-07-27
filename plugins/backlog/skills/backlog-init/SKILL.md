---
name: backlog-init
description: Cria o armazenamento e backlogs v2 suportados.
argument-hint: "--db PATH --code CODE --name NAME [--profile PROFILE]"
user-invocable: true
disable-model-invocation: true
---
# Inicializar

Para armazenamento novo, execute `backlogctl [--json] store init --db PATH`. Para backlog, confirme e execute `backlogctl [--json] backlog create --db PATH --code CODE --name NAME [--profile PROFILE]`. Não invente profile/category. Em sucesso, valide o envelope; em falha, stderr/exit 1 ou usage/exit 2.