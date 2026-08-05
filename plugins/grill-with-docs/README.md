# grill-with-docs v2.1.1 — Delivery First

Plugin plan-only para entrevistar decisões arquiteturais sem colisão entre worktrees.

```text
feature/fix/hotfix → .grill/work-items/<work-id>/ → audit → PLAN_ONLY_STOP
                                                         │
ship externo → complete/GO ─────────────────────────────┴→ reconcile → .grill/global/
```

## Hotfix-fast / incidente

```bash
python3 "$CORE" hotfix "$PWD" --slug auth-timeout --scope src/auth.py --reproduction "curl /login returns 500" --evidence "incident-2026-08-05.log" --correction-test "tests/test_auth.py::test_timeout" --rollback "revert commit X" --constitution-evidence evidence/constitution.txt --test-command "python3 -c 'raise SystemExit(0)'" --test-timeout 30
python3 "$CORE" hotfix-go "$PWD" --work-id <work-id>
python3 "$CORE" audit "$PWD" --work-id <work-id>
```

``hotfix` retorna HOTFIX-PREPARED; `hotfix-go` revalida e executa o teste antes de emitir HOTFIX-GO. HOTFIX-GO é autocontido e fail-closed; não exige ROADMAP/BL/DQ/reconciliação para segurança. Full audit e reconciliação são pós-ship. Feature/fix continuam `PLAN_ONLY_STOP`.

## Início rápido

```bash
CORE="$PLUGIN_ROOT/skills/grill-with-docs/scripts/grill_workspace.py"
python3 "$CORE" init "$PWD" --type feature --slug minha-feature
python3 "$CORE" hotfix-go "$PWD" --work-id <work-id>
python3 "$CORE" audit "$PWD" --work-id <work-id>
```

Após o `PLAN_ONLY_STOP`, faça o ship externamente. Quando a fase estiver `complete` e a auditoria retornar `GO`, gere o preview de reconciliação:

```bash
python3 "$CORE" reconcile "$PWD" --source-root ../outra-worktree
```

Aplicação da projeção global:

```bash
python3 "$CORE" reconcile "$PWD" --apply --integration-branch main
```

Migração legada, sempre preview-first:

```bash
python3 "$CORE" migrate "$PWD" --type fix --slug migracao
python3 "$CORE" migrate "$PWD" --type fix --slug migracao --apply
```

## Contrato

- Um bundle completo por work item em `.grill/work-items/<work-id>/`.
- `WORKFLOW.md` e a Constituição são project-wide.
- Constituição ausente é `not-present`; presente é read-only e inviolável.
- `CONSTITUTION-CHECK.md` exige cobertura por cláusula, evidência e justificativa.
- Auditoria, hooks e reconcile preview são read-only; reconcile só ocorre depois de `PLAN_ONLY_STOP` e do ship externo com fase `complete`/auditoria `GO`.
- O global é projeção determinística; nunca é fonte de verdade.
- IDs locais tornam-se `<work-id>/<ID>` na projeção.
- A sessão encerra em `PLAN_ONLY_STOP`, antes de implementação.

## Exit codes

| Código | Resultado |
|---:|---|
| 0 | GO, PREVIEW, APPLIED, CREATED ou REUSED |
| 1 | NO-GO |
| 2 | BLOCKED ou erro de uso |
| 3 | BLOCKED-CONSTITUTION |

Consulte `skills/grill-with-docs/SKILL.md` e `references/session-protocol.md` para o protocolo normativo.
