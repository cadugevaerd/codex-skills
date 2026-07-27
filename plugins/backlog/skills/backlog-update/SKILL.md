---
name: backlog-update
description: Verifica e recupera a instalação assinada por SHA-256 do backlogctl.
argument-hint: "--db PATH"
user-invocable: true
disable-model-invocation: true
---
# Atualizar

Use o caminho exato emitido pelo hook de bootstrap SessionStart para executar `backlogctl [--json] doctor --db PATH` e `backlogctl --version`; nunca presuma que está no PATH. Em recuperação manual, execute `node plugins/backlog/scripts/ensure-backlogctl.js --install-dir DIR` e use o caminho retornado. O verificador baixa somente o release imutável e valida SHA-256 antes da instalação; não manipule SQLite diretamente.