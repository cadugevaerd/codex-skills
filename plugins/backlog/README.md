# Backlog plugin 2.4.2

Plugin cross-runtime para `backlogctl` **2.4.0**, DB schema **5**, envelope contract **2** e documento de import contract **3**.

## Distribuição

O bootstrap escolhe o asset por OS/arquitetura, aceita somente release HTTPS imutável, verifica SHA-256 e executa `backlogctl version` antes da troca atômica. No Claude Code, o hook `SessionStart` informa o caminho exato; no Codex, execute `node plugins/backlog/scripts/ensure-backlogctl.js --install-dir DIR`.

A operação é fail-closed: confirme caminho, versão, `doctor`, schema/capability e SHA. Nunca presuma `PATH`, leia SQLite diretamente ou use fallback legado.

## Superfície

`store init`, `backlog`, `item`, `context`, `decision`, `format`, `export`, `merge`, `import`, `todo`, `update` e `doctor`.

- Import nativo: JSON v3, `preview` e `apply --confirm --expected-sha256 SHA`.
- Merge: proposta `MRG-N` com snapshots/revisions e apply confirmado.
- TODO/FIXME: software-only, opt-in, scan puro e apply confirmado por SHA.
- JSON v1: migração agent-led separada; nunca é aceito pelo import nativo.

Use `references/contract.md` como autoridade.
