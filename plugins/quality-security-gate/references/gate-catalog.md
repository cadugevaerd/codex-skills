# Catálogo de gates

## Estados

- `AUTOMATED_ENFORCED`: execução automática comprovada e falha bloqueia merge/release/deploy protegido.
- `AUTOMATED_NOT_ENFORCED`: executa, mas não bloqueia a operação.
- `AUTOMATED_UNVERIFIED`: configuração encontrada sem execução/enforcement comprovados.
- `MANUAL`: depende de ação humana.
- `ABSENT`: controle não implementado.
- `UNKNOWN`: evidência insuficiente ou acesso indisponível.

Presença de YAML, script ou badge não prova automação. Exija configuração parseada, execução identificável, resultado íntegro e prova de enforcement quando o gate for obrigatório.

## Gates por risco

| Gate | Propósito | Módulos principais | P1 | P2 | P3 |
|---|---|---|---:|---:|---:|
| `GATE-001` | Governança e snapshot íntegros | MOD-001, MOD-012 | obrigatório | obrigatório | obrigatório |
| `GATE-002` | Qualidade/testes automatizados | MOD-003 | obrigatório | obrigatório | obrigatório |
| `GATE-003` | Segurança básica e integração protegida | MOD-002, MOD-004 | obrigatório | obrigatório | obrigatório |
| `GATE-004` | Supply chain, CI/CD e superfície técnica | MOD-005, MOD-006, MOD-007, MOD-008, MOD-009, MOD-010 | — | obrigatório | obrigatório |
| `GATE-005` | Produção, dados sensíveis, observabilidade e resposta | MOD-010, MOD-011, MOD-012 | — | — | obrigatório |

O perfil define o conjunto mínimo; um módulo pode encontrar riscos adicionais e elevar o resultado, nunca reduzir silenciosamente o perfil.

## Resultado

- `PASS`: gate executado/validado com evidência suficiente.
- `FAIL`: falha de controle comprovada; overall `NO-GO` se não houver bloqueio de integridade.
- `BLOCKED`: evidência, capacidade, sandbox, acesso ou integridade insuficientes; overall `BLOCKED`.
- `N/A`: não aplicabilidade demonstrada e permitida pela matriz de risco.

## Evidência obrigatória

Toda evidência deve estar vinculada ao snapshot e conter fonte verificável. Resultados de comandos devem registrar ferramenta/versão, argumentos estruturados, diretório, exit code, completude e digest do relatório. Timeout, zero testes, relatório truncado/malformado ou ferramenta ausente nunca são `PASS`.