<!-- grill-with-docs-constitution:v1 -->
# Grill Constitution

- version: 1.0.0
- ratified: {{RATIFIED}}
- last-amended: {{LAST_AMENDED}}

## Core Principles

### Evidência antes de afirmação
Toda afirmação verificável MUST ser acompanhada de evidência legível e rastreável.

### Work item isolado e ownership
Cada feature, fix ou hotfix MUST possuir work item isolado, identidade imutável e ownership explícito.

### Feature/fix plan-only
Feature e fix terminam em PLAN_ONLY_STOP; nenhum plano autoriza alteração ou publicação.

### Sequência obrigatória do desenvolvimento
O desenvolvimento MUST seguir, sem saltos: specify, plan, checklist, tasks, analyze, agent-assign, agent-execute, converge, verify, review, ship.

### Verify/review antes de ship
Ship somente pode iniciar após verify e review completos, com evidências.

### Fail-closed sem waiver
Ambiguidade, corrupção, ausência de evidência ou violação MUST bloquear; não existe waiver implícito.

### Rastreabilidade
Decisões, mudanças, fases, módulos, DUs, receipts e gates MUST ser rastreáveis ao work item e ao commit.

## Governance

Esta Constituição é autoridade normativa do projeto. Alterações exigem versão SemVer, data ISO, evidência, revisão e registro no work item. Hooks são somente leitura. A Constituição preexistente humana ou gerenciada é preservada byte a byte e continua autoridade.
