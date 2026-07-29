# grill-with-docs (Codex)

Versão Codex 1.2.0 do workflow documental auditável.

## Contrato runtime

- `/grill-with-docs iniciar` e `/grill-with-docs retomar` criam ou validam `WORKFLOW.md` e materializam incrementalmente as oito entradas Spec Kit:
  1. `.specify/memory/constitution.md`;
  2. `WORKFLOW.md`;
  3. `CONTEXT.md`;
  4. `docs/adr/`;
  5. `ROADMAP.md`;
  6. `DECISION-BACKLOG.md`;
  7. `PLAN-CONTEXT.md`;
  8. `handoffs/FASE-NNN-SPECIFY-HANDOFF.md`.
- `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl`, `state.json` e `AUDIT.md` são auxiliares auditáveis, não entradas adicionais.
- `/grill-with-docs auditar` é **read-only**: apenas valida o workflow e os documentos existentes.
- Os hooks `SessionStart` e `SubagentStart` apenas injetam contexto. Eles exigem trust explícito via `/hooks`; não executam o workflow nem fazem merge.
- A skill termina em `PLAN_ONLY_STOP`: não chama `specify`, não implementa código e não cria branch, commit ou merge. O executor posterior entrega somente o handoff selecionado ao `specify`.
- Não há alias de comando nem merge automático.

Instalação, a partir da raiz do marketplace:

```bash
codex plugin marketplace add .
codex plugin add grill-with-docs@codex-skills
```
