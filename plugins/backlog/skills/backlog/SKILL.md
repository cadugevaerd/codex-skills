---
name: backlog
description: Encaminha intenções para operações Backlog v2 implementadas.
argument-hint: "backlog|item|context|format|export|doctor|import"
user-invocable: true
disable-model-invocation: false
---
# Backlog v2

`backlogctl` é fornecido pelo bootstrap verificado. No Claude Code, o hook SessionStart instala/reutiliza o binário e fornece o caminho exato; invoque esse caminho, nunca presuma PATH. No Codex, use o caminho emitido por recuperação manual (`node plugins/backlog/scripts/ensure-backlogctl.js --install-dir DIR`). Nunca leia ou escreva SQLite diretamente. Use `store init`, `doctor`, `backlog create|list|show|edit|archive|bind`, `item add|list|show|edit|transition|move`, `context add|list|show|supersede|revoke|expire`, `format list|show|propose|apply` e `export json|markdown|consolidated`. `--json` vem antes da família; `--db PATH` é flag do comando.

Itens têm `title` como resumo e `description` como a descrição executável completa. `item add --description TEXT` grava a descrição; `item edit --description TEXT` substitui, flag omitida preserva e string vazia limpa. JSON de item em show/list/export sempre contém `description`, inclusive `""`.

Toda mutação de contexto exige confirmação explícita do usuário e deve usar `backlogctl --json context ... --db PATH`; nunca leia/escreva SQLite ou JSON diretamente.

A skill `backlog-import` é o workflow agent-led V1 JSON → V2: primeiro lê e valida o JSON inteiro, incluindo descrições legadas completas, roda doctor e apresenta uma proposta completa sem mutação; somente após confirmação humana explícita executa o plano com store init/backlog create|bind/item add --description/transition|move pelo caminho exato do backlogctl. Ela não é um comando CLI, não modifica o legado e emite mapa `legacy_id → v2_id`. A migração cross-item não é atômica; falha com IDs já criados e relatório para retomada.

Para `format propose`, mostre o diff estruturado e aguarde confirmação humana explícita; não altere itens. Execute `format apply` somente após confirmação explícita, com `--confirm`. Não há confirmação oculta. Não tente novamente erros de proposta obsoleta, expirada ou de confirmação: explique o status e gere nova proposta quando solicitado.

`merge`, `import` e `update` não são comandos CLI implementados; `import` designa somente o workflow da skill acima. Não os trate como operações disponíveis.

Sucesso JSON é o envelope v2 documentado em `references/contract.md`. Erros de domínio são stderr/exit 1; uso inválido é stderr/exit 2.

## Contract v2.0.2
The inventory includes `item reconcile-status` and `item archive` as audited administrative operations. Both require `--reason` and `--confirm`; reconcile bypasses the graph only for verified human-approved repair, and archive is soft archival. They are not normal migration or transition flows.
