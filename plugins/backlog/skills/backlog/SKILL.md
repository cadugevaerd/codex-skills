---
name: backlog
description: Encaminha intenções para operações Backlog v2 implementadas.
argument-hint: "backlog|item|context|format|export|doctor"
user-invocable: true
disable-model-invocation: false
---
# Backlog v2

`backlogctl` compatível com o contrato 2.0 deve estar instalado. Execute primeiro `backlogctl --json doctor --db PATH`. Use `store init`, `doctor`, `backlog create|list|show|edit|archive|bind`, `item add|list|show|edit|transition|move`, `context add|list|show|supersede|revoke|expire`, `format list|show|propose|apply` e `export json|markdown|consolidated`. `--json` vem antes da família; `--db PATH` é flag do comando.

Toda mutação de contexto exige confirmação explícita do usuário e deve usar `backlogctl --json context ... --db PATH`; nunca leia/escreva SQLite ou JSON diretamente.

Para `format propose`, mostre o diff estruturado e aguarde confirmação humana explícita; não altere itens. Execute `format apply` somente após confirmação explícita, com `--confirm`. Não há confirmação oculta. Não tente novamente erros de proposta obsoleta, expirada ou de confirmação: explique o status e gere nova proposta quando solicitado.

`merge`, `import` e `update` não estão implementados (ou são apenas diagnosticáveis); não os trate como operações disponíveis.

Sucesso JSON é o envelope v2 documentado em `references/contract.md`. Erros de domínio são stderr/exit 1; uso inválido é stderr/exit 2.