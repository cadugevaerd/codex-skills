# ROADMAP

- execution-order: FASE-001

## FASE-001 — <!-- nome estável da fase -->
- state: planned
- objetivo: <!-- resultado observável -->
- scope-in: <!-- incluído -->
- scope-out: <!-- excluído -->
- context-refs: <!-- termos canônicos de CONTEXT.md -->
- ADRs: none
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md

> `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.
