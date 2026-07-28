---
name: backlog-merge
description: Inspeciona e aplica merges somente após snapshots, revisions e confirmação.
argument-hint: "preview|list|show|apply|expire --db PATH"
user-invocable: true
disable-model-invocation: true
---
# Merge

Resuma origem, destino, leitura/mutação e confirmação. `merge preview --source SRC --target DST --db PATH` produz proposta auditável `MRG-N`; `list|show` consultam e `expire --id MRG-N` invalida.

Execute `merge apply --id MRG-N --db PATH --confirm` somente após confirmação explícita. A CLI revalida revisions, expiração e estado. Não existe hash de merge; conflito/stale/erro encerra sem mutação.
