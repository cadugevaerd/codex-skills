---
name: backlog-import
description: Importa JSON v3 estrito com preview, confirmação e SHA-256; separa migração v1.
argument-hint: "preview|apply --file JSON_V3_PATH --expected-sha256 SHA --db PATH"
user-invocable: true
disable-model-invocation: true
---
# Import nativo JSON v3

Resuma arquivo, validações, leitura/mutação, confirmação e SHA. Execute `<BACKLOGCTL> --json import preview --file FILE --db PATH` sem mutação. Só após confirmação execute `<BACKLOGCTL> --json import apply --file FILE --db PATH --expected-sha256 SHA --confirm`.

Divergência encerra fail-closed com stderr/exit reais. JSON v1 não é aceito diretamente; use o workflow agent-led de `references/migration-v1-to-v2.md`.
