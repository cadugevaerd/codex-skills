# grill-with-docs (Codex)

Versão Codex 1.2.0 do workflow documental auditável.

## Contrato runtime

- `/grill-with-docs iniciar` e `/grill-with-docs retomar` criam ou validam `WORKFLOW.md` e geram oito entradas Spec Kit.
- `/grill-with-docs auditar` é **read-only**: apenas valida o workflow e os documentos existentes.
- Os hooks `SessionStart` e `SubagentStart` apenas injetam contexto. Eles exigem trust explícito via `/hooks`; não executam o workflow nem fazem merge.
- `specify` recebe somente o handoff da fase selecionada, nunca o workflow inteiro, e para em `PLAN_ONLY_STOP`.
- Não há alias de comando nem merge automático.

Instalação, a partir da raiz do marketplace:

```bash
codex plugin marketplace add .
codex plugin add grill-with-docs@codex-skills
```
