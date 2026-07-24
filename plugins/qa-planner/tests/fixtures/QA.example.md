# QA Plan

<!-- qa-planner:start -->
## 1. Identificação

| Campo | Valor |
|---|---|
| Status do plano | READY |
| Repositório | `payments-api` |
| Raiz analisada | `/workspace/payments-api` |
| Branch alvo | `feat/idempotency-key` |
| Base | `main` |
| HEAD SHA | `0123456789abcdef0123456789abcdef01234567` |
| Range de diff | `fedcba9876543210fedcba9876543210fedcba98..HEAD` |
| Alterações locais incluídas | não |
| Caminho do QA.md | `QA.md` |
| Justificativa do local | O diff abrange mais de um módulo; a raiz é o escopo de lifecycle. |

## 2. Evidências consultadas

| ID | Fonte | Tipo | O que comprova |
|---|---|---|---|
| EVD-001 | `docs/specs/idempotency.md` | requisito | A mesma chave não pode criar cobranças duplicadas. |
| EVD-002 | `src/routes/charges.py` | diff | A rota passou a aceitar o header `Idempotency-Key`. |
| EVD-003 | `tests/api/test_charges.py` | teste | A suíte de API existente cobre criação de cobrança. |

## 3. Requisitos e critérios de aceite

| ID | Status | Requisito / critério de aceite | Evidência |
|---|---|---|---|
| REQ-001 | confirmado | Repetir a mesma requisição com a mesma chave retorna a cobrança originalmente criada. | EVD-001; EVD-002 |
| REQ-002 | inferido | Chaves iguais com payload diferente devem retornar erro sem criar uma segunda cobrança. | EVD-001; EVD-002 |

## 4. Rastreabilidade

| Requisito / risco | Cenários | Prioridade |
|---|---|---|
| REQ-001; RISK-002 | QA-001 | P0 |
| REQ-002; RISK-001 | QA-002 | P0 |

## 5. Escopo e fora de escopo

### No escopo

- Criação de cobrança com `Idempotency-Key`.
- Repetição de requisição e conflito de payload.

### Fora de escopo

- Retenção histórica de chaves após a janela definida pela infraestrutura; prazo não consta nas evidências.

## 6. Estratégia de testes

| Risco | Probabilidade | Impacto | Prioridade | Abordagem |
|---|---|---|---|---|
| RISK-001 — cobrança duplicada | média | alto | P0 | API e integração com persistência |
| RISK-002 — resposta inconsistente ao retry | média | médio | P1 | API |

- **Critério de entrada:** ambiente de teste com banco isolado e credencial de API não produtiva.
- **Critério de saída:** cenários P0 e P1 executados ou bloqueios registrados com evidência.

## 7. Ambiente, dados e dependências

| Item | Necessidade | Fonte / observação |
|---|---|---|
| Ambiente | ambiente de teste | TBD — não encontrado nas evidências |
| Dados | conta pagadora válida | fixture existente em `tests/api/test_charges.py` |
| Dependência | banco isolado | rota persiste a cobrança em `src/routes/charges.py` |

## 8. Cenários detalhados

### QA-001 — Repetição com a mesma chave retorna a cobrança original

- **Rastreabilidade:** REQ-001; RISK-001; RISK-002
- **Prioridade:** P0
- **Nível/tipo:** API e integração
- **Automação:** recomendada
- **Status inicial:** NOT_RUN
- **Pré-condições e dados:** conta pagadora válida e banco de teste vazio.
- **Passos:**
  1. Enviar uma criação de cobrança com um payload válido e `Idempotency-Key: chave-001`.
  2. Reenviar a mesma requisição com a mesma chave.
- **Resultado esperado:** a segunda resposta referencia a mesma cobrança da primeira e nenhuma cobrança adicional é persistida.
- **Evidência a coletar:** IDs das respostas, contagem de cobranças persistidas e log de correlação.
- **Comando/harness candidato:** `pytest tests/api/test_charges.py -q` — EVD-003

### QA-002 — Mesma chave com payload diferente não cria cobrança adicional

- **Rastreabilidade:** REQ-002; RISK-001
- **Prioridade:** P0
- **Nível/tipo:** API e integração
- **Automação:** recomendada
- **Status inicial:** NOT_RUN
- **Pré-condições e dados:** cobrança inicial criada com `Idempotency-Key: chave-001`.
- **Passos:**
  1. Reenviar a criação com `Idempotency-Key: chave-001` e valor diferente.
- **Resultado esperado:** a API retorna erro de conflito documentado e a contagem de cobranças permanece inalterada.
- **Evidência a coletar:** status HTTP, payload de erro e contagem de cobranças persistidas.
- **Comando/harness candidato:** `pytest tests/api/test_charges.py -q` — EVD-003

## 9. Regressão necessária

- Criação de cobrança sem `Idempotency-Key` continua seguindo o contrato pré-existente.
- Repetição de requisições com chaves distintas cria cobranças distintas.

## 10. Candidatos à automação

| Cenário | Camada sugerida | Local/harness candidato | Motivo |
|---|---|---|---|
| QA-001 | API e integração | `tests/api/test_charges.py` | Fluxo determinístico e crítico. |
| QA-002 | API e integração | `tests/api/test_charges.py` | Previne duplicidade financeira. |

## 11. Dúvidas, suposições e bloqueios

- **Pergunta:** qual é o status HTTP e o payload canônico para conflito de chave com payload divergente?
- **Impacto:** QA-002 precisa ajustar a asserção exata.
- **Origem:** o comportamento está inferido do diff; a especificação não define a resposta de erro.

## 12. Handoff para a IA executora

1. Confirme que branch e `HEAD SHA` ainda correspondem à seção 1.
2. Execute somente os cenários `QA-*` aplicáveis.
3. Registre comando, entrada, saída real, evidência e timestamp em `QA-RESULTS.md`.
4. Preserve `QA.md` como plano; não substitua cenários por resultados.
5. Use somente `PASS`, `FAIL`, `BLOCKED` ou `SKIPPED` em `QA-RESULTS.md`.
6. Se ambiente, dados ou dependência estiver indisponível, registre `BLOCKED`; nunca invente resultado.

Planejamento de QA encerrado. Nenhum teste foi executado.
<!-- qa-planner:end -->
