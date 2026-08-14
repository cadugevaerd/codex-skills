# LangGraph Architecture para Codex

Plugin com duas skills e dois custom agents isolados:

| Skill | Agente obrigatório | Modelo | Sandbox |
|---|---|---|---|
| `/langgraph-architecture-plan` | `langgraph_architect` | `gpt-5.6` + `max` | `read-only`; o agente principal persiste o plano devolvido |
| `/langgraph-repository-review` | `langgraph_reviewer` | `gpt-5.6` + `max` | `read-only` |

## Instalação

```bash
codex plugin add langgraph-architecture@codex-skills
```

As skills ficam disponíveis imediatamente. Para registrar os custom agents, execute uma vez no clone do marketplace:

```bash
python3 plugins/langgraph-architecture/scripts/install_codex_agents.py
```

Teste isolado:

```bash
python3 plugins/langgraph-architecture/scripts/install_codex_agents.py --codex-home /tmp/codex-langgraph-test
```

Remoção:

```bash
python3 plugins/langgraph-architecture/scripts/install_codex_agents.py --uninstall
```

O instalador é idempotente, preserva configuração preexistente, cria backup antes da primeira alteração e mantém um marker de ownership com hashes dos agents e inventário do bundle. Ele falha fechado diante de roles, arquivos ou diretórios não gerenciados, symlinks e conteúdo gerenciado alterado; o uninstall remove somente o payload comprovadamente pertencente ao plugin.

## Uso

```text
/langgraph-architecture-plan repo=. planeje um chatbot corporativo com RAG
/langgraph-repository-review repo=. revise esta implementação e liste os problemas
```

A primeira skill cria somente `LANGGRAPH-ARCHITECTURE-PLAN.md`. A segunda é estritamente read-only. Se os agents não estiverem registrados, as skills retornam `BLOCKED`; não fazem fallback para o agente principal.
