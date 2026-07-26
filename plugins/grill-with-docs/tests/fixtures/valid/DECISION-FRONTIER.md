# DECISION FRONTIER

## DQ-0001 — Escolher contrato da API
- phase: FASE-001
- fingerprint: escolher contrato api fornecedor
- impact: high
- state: resolved
- context-refs: Tenant, API
- artifacts: ADR-0001, ROADMAP.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — Confirmar limite por tenant
- phase: FASE-002
- fingerprint: confirmar limite tenant fornecedor
- impact: medium
- state: deferred
- context-refs: Tenant
- artifacts: BL-0001, ROADMAP.md
- depends-on: DQ-0001
- final-ref: BL-0001
