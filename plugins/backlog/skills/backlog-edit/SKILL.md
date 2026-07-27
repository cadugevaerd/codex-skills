---
name: backlog-edit
description: Edita campos suportados de backlog ou item.
argument-hint: "--db PATH --code CODE [flags de edição]"
user-invocable: true
disable-model-invocation: true
---
# Editar

Após doctor, snapshot e confirmação, execute `backlogctl [--json] backlog edit --db PATH --code CODE ...` ou `item edit --db PATH --id ID ...` com os campos aceitos pelo runtime. Para item, `--description TEXT` substitui a descrição completa; omitir a flag preserva o valor; `--description ""` limpa explicitamente. Altere somente campos solicitados e valide o envelope; falhas não autorizam fallback direto.