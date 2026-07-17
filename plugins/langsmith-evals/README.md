# LangSmith Evals para Codex

Plugin LangSmith-first com uma skill compartilhada e dois custom agents:

- `langsmith_evals_engineer`: implementa datasets, evaluators, experiments, backtests e gates.
- `langsmith_evals_auditor`: revisa evidencias de forma independente e emite `GO`, `NO-GO` ou `BLOCKED`.

## Instalacao do plugin

```bash
codex plugin add langsmith-evals@codex-skills
```

A skill `/langsmith-evals` funciona imediatamente no agente principal.

## Ativacao dos custom agents

A especificacao atual de plugins Codex distribui skills e MCP, mas nao registra custom agents automaticamente. Por isso este plugin inclui um instalador idempotente que copia os TOMLs e registra os papeis em `~/.codex/config.toml`:

```bash
python3 plugins/langsmith-evals/scripts/install_codex_agents.py
```

Teste sem alterar seu perfil:

```bash
python3 plugins/langsmith-evals/scripts/install_codex_agents.py --codex-home /tmp/codex-evals-test
```

Remocao:

```bash
python3 plugins/langsmith-evals/scripts/install_codex_agents.py --uninstall
```

Os dois TOMLs fixam explicitamente:

```toml
model = "gpt-5.6-terra"
```

O Engineer usa sandbox `workspace-write`; o Auditor usa sandbox `read-only` e nao pode fabricar ou corrigir a propria evidencia.
