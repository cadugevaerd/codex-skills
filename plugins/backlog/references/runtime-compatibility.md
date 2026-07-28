# Compatibilidade de runtime

Compatível com `backlogctl` release **v2.1.0**, DB schema **5**, envelope contract **2** e import document contract **3**.

No Claude Code, use o executável exato emitido pelo hook `SessionStart`. No Codex, use a recuperação manual e o caminho retornado. Nunca presuma `PATH`.

O bootstrap valida manifesto HTTPS imutável, OS/arquitetura, SHA-256 e `backlogctl version`; só reutiliza binário com hash e versão válidos. Falhas de download, redirect, checksum, versão ou plataforma são fail-closed.
