---
name: backlog-update
description: Verifica, atualiza e migra backlogctl 2.1 com SHA-256, rollback e backup.
argument-hint: "check|install|migrate"
user-invocable: true
disable-model-invocation: true
---
# Atualizar

Use o caminho exato retornado pelo bootstrap; nunca presuma `PATH`.

1. `<BACKLOGCTL> --json update check --manifest URL_OR_PATH` valida release/plataforma sem mutar.
2. Após confirmação: `<BACKLOGCTL> --json update install --manifest URL_OR_PATH --install-dir DIR --confirm`; SHA e `version` são verificados antes/depois do rename e falha restaura o anterior.
3. `<BACKLOGCTL> --json update migrate --db PATH --backup-dir DIR --confirm` exige DB existente, integrity check e backup; bloqueia schema futuro.
4. Execute `<BACKLOGCTL> --json doctor --db PATH` após atualização.

Claude usa o hook automático. No Codex: `node plugins/backlog/scripts/ensure-backlogctl.js --install-dir DIR [--expected-sha256 SHA]`.
