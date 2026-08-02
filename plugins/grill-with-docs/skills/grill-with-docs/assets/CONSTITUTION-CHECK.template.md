# Constitution Check

Este bloco é gerenciado por `grill_workspace.py`. Não remova os marcadores.

<!-- grill-constitution-check:start -->
```json
{
  "constitution_state": "present",
  "constitution_sha256": "{{CONSTITUTION_SHA256}}",
  "clauses": [
    {
      "id": "{{CLAUSE_ID}}",
      "heading": "{{CLAUSE_HEADING}}",
      "status": "PENDING",
      "evidence": [],
      "justification": ""
    }
  ]
}
```
<!-- grill-constitution-check:end -->

Somente `PASS` e `NOT-APPLICABLE`, ambos com evidência e justificativa, liberam auditoria. Não existe waiver constitucional por ADR.
