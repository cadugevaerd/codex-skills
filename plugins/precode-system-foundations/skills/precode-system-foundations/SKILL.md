---
name: precode-system-foundations
description: Inspeciona evidências de um projeto e mantém uma fundação pré-código corrigível, sem converter inferência em decisão.
version: 1.1.0
author: Hermes
---
# Pre-code System Foundations

Use antes de implementar. Inspecione o repositório (código, testes e docs) e registre cada módulo com `necessary`, `existing`, `missing`, `invalid` ou `not-verifiable`, sempre com evidência e confiança (`verified`, `inferred`, `unknown`). Inferências são hipóteses revisáveis, nunca decisões.

## Contrato operacional
1. Declare escopo, usuários, resultado e dono das decisões.
2. Inspecione contexto real antes de classificar; cite caminhos, testes ou decisões do usuário.
3. Atualize o estado com `scripts/foundationctl.py`, preservando `change_log` append-only.
4. Recomende separadamente `mvp`, `go_live` e `future`; use `decision_status: proposed` até aprovação explícita. Perguntas abertas bloqueiam decisões materiais.
5. Valide semanticamente e entregue uma leitura que permita correção posterior.

## CLI
`python3 scripts/foundationctl.py init foundation.json --project Nome`
`python3 scripts/foundationctl.py validate foundation.json`
`python3 scripts/foundationctl.py apply-patch foundation.json patch.json`

O CLI aceita JSON Patch limitado a `add`, `remove`, `replace` e `test`, aplica em cópia, rejeita qualquer estado inválido e grava atomicamente. IDs de módulos seguem `MOD-NNN`; IDs de mudanças são únicos. O bundle é framework/database-neutral: não invente componentes, autorização, invariantes ou isolamento sem evidência. A fundação não é aprovação de produção.
