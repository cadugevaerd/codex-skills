# Backlog plugin

## Runtime bootstrap

Claude Code runs `scripts/ensure-backlogctl.js --hook` at SessionStart. It downloads the immutable v2.0.0 release only after SHA-256 verification, reuses a matching installation, and emits the exact executable path. Invoke that path; do not assume `backlogctl` is on PATH.

For Codex, no automatic install hook is claimed. If recovery is needed, run `node plugins/backlog/scripts/ensure-backlogctl.js --install-dir DIR` and invoke the exact returned path. The installer never manipulates SQLite.
