# Priorização e contextos

A ordenação canônica é criticality (`critical`, `high`, `medium`, `low`) e depois position; não há limite artificial de position. Status são `open`, `in_progress`, `done`, `cancelled`, `merged`; `blocked` é condição.

A família `context` está implementada: `add|list|show|supersede|revoke|expire`. Execute-a como `backlogctl --json context ... --db PATH`; mutações exigem confirmação explícita do usuário. Nunca execute acesso direto ao SQLite.

Para formatos, `format list|show|propose|apply` está implementado. Mostre o diff de `format propose` e aguarde confirmação humana explícita; execute `format apply` somente após confirmação, com `--confirm`.