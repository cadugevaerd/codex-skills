# ROADMAP

## FASE-001 — Integração de API
- state: ready-for-specify
- objetivo: integrar a API do fornecedor
- scope-in: cliente HTTP e autenticação
- scope-out: limite por tenant
- context-refs: Tenant, API
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- entrada: ADR aceito
- saída: requisitos da integração delimitados
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md

## FASE-002 — Limite por tenant
- state: planned
- objetivo: aplicar limite confirmado por fornecedor
- scope-in: política de limite
- scope-out: faturamento
- context-refs: Tenant
- ADRs: none
- ADRs-justificativa: depende da evidência do fornecedor
- BLs: BL-0001
- depends-on: FASE-001
- entrada: limite oficial publicado
- saída: política aprovada
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
