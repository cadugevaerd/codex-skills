<!-- grill-with-docs-workflow:v2 -->
# Spec Kit Workflow (project-wide)

Generic, project-independent contract. Requires Spec Kit >=0.11.2 and verified extensions: `git`, `agent-assign`, `bugfix`, `verify-review-ship`.

## Loop externo: ROADMAP e handoff
ROADMAP.md is the fixed, rarely renumbered phase order. Only one phase is `ready`; the previous phase must be `complete`. Check blockers before starting, record the decision, and create a single handoff for the next phase. `specify` receives only that handoff, never the whole roadmap. `before_specify` and branch/worktree checks happen before specify. The spec number is sequential and is not the phase number.

## Delivery First / hotfix-fast
Feature e fix permanecem plan-only. Incidentes podem usar `grill_workspace.py hotfix` com escopo fechado, reprodução/evidência, teste de correção, rollback e verificação constitucional. Essa trilha não depende do ROADMAP/BL/DQ nem do workflow global para decidir HOTFIX-GO; reconciliação e auditoria documental completa são pós-ship.

## Limite desta skill: PLAN_ONLY_STOP

Este documento descreve um ciclo que será executado externamente. Durante `grill-with-docs`, `PLAN_ONLY_STOP` ocorre **antes de `specify`**: a skill prepara e audita entradas, entrega o path do handoff selecionado e para. Ela não chama `specify`/`plan`, não edita código e não cria branch, commit ou merge.

## Ciclo externo de execução (11 etapas)
`specify → plan → checklist → tasks → analyze → agent-assign → agent-execute → converge → verify → review → ship`.
Analyze is after tasks; converge is before verify; ship is direct, without a PR. Deliverable/return table:

| Step | Deliverable | Return when blocked |
|---|---|---|
| specify | numbered WHAT/WHY spec | clarify handoff |
| plan | design and gates | specify |
| checklist | acceptance checklist | plan |
| tasks | ordered bounded tasks | plan |
| analyze | risks/dependencies | tasks |
| agent-assign | ownership and file scopes | tasks |
| agent-execute | scoped evidence | agent-assign |
| converge | integrated result | tasks/analyze |
| verify | test/gate evidence | converge |
| review | approved review | converge/verify |
| ship | release and state update | review/verify |

O ciclo acima pertence ao executor posterior, nunca à sessão `grill-with-docs` que já terminou em `PLAN_ONLY_STOP`.

## ship: phases A–E (A-E)
A. Record approved learnings only. B. Revalidate artifacts, tests, constitution, and release assumptions. C. Merge the worktree with `git merge --no-ff`, run all gates, and stop on failure. D. Push directly (no PR), reread the pushed ref and verify its hash. E. Clean temporary worktrees/branches and report cleanup warnings; never hide cleanup warnings. (cleanup warnings are always surfaced.)

## Fim do ciclo
Mark the current ROADMAP phase `complete` and the next phase `ready`; record blockers and handoff. Update DECISION-BACKLOG.md, create/update the applicable ADR, and update the glossary. Preserve traceability.

## Project-wide artifacts and governance
Exact artifacts: `.specify/memory/constitution.md`, `WORKFLOW.md`, `CONTEXT.md`, `docs/adr/`, `ROADMAP.md`, `DECISION-BACKLOG.md`, `PLAN-CONTEXT.md`, `handoffs/FASE-NNN-SPECIFY-HANDOFF.md`. Constitution is governance and cannot be invented or silently replaced. Keep `docs/adr/` canonical; legacy `adrs/` requires migration. Auxiliary artifacts are `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl`, `state.json`, and `AUDIT.md`.

## Release and safety notes
Use the git/agent-assign/bugfix/verify-review-ship extensions with the stated minimum version. For release zip artifacts, fingerprint inputs and verify the executable bit (`chmod +x`) plus an actual execution test. Fingerprint workflow and constitution in state. Do not overwrite an incompatible human WORKFLOW. This file is generic and contains no project data.
