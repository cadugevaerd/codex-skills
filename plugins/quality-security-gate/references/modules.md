# Contratos dos módulos

Todos os módulos investigam o mesmo snapshot e apenas observam. Cada saída deve indicar o gate examinado, automação, evidência, status, correção necessária e validação futura.

| Módulo | O que investigar | Evidência mínima | Quando falha | Validação pós-correção a prescrever |
|---|---|---|---|---|
| **MOD-001 Governança** | Instruções do repositório, ownership, política de segurança, contribuição e exceções | Paths/trechos, responsáveis e regras parseadas | Regra crítica ausente, contraditória ou sem owner | Reprocessar documentos e provar owner/critério explícitos |
| **MOD-002 Proteção de integração** | PR reviews, required checks, proteção de branch/tag, merge e assinatura | Config local e, quando autorizado, API read-only do provedor | Check existe mas não bloqueia merge; bypass não governado | Demonstrar PR negativa bloqueada e configuração enforced |
| **MOD-003 Qualidade de código** | Formatação, lint, type-check, build, unit/integration tests e cobertura aplicável | Comandos allowlisted, exit codes, contagem de testes e relatório íntegro | Zero testes, subset indevido, cache stale ou gate ausente | Executar fixture positiva/negativa e suíte canônica no CI |
| **MOD-004 Secrets e credenciais** | Secret scanning, arquivos sensíveis, redaction e política de rotação | Config parseada e scan autorizado com fixture sintética | Secret exposto, scanner ausente/manual ou saída vazada | Fixture sintética deve falhar sem registrar o segredo |
| **MOD-005 SAST e políticas** | SAST, regras de segurança, severidade, suppressions e enforcement | Config/versão, relatório completo e check obrigatório | Scanner indisponível, findings críticos ignorados ou suppressions sem escopo | Fixture vulnerável deve gerar finding e bloquear o fluxo |
| **MOD-006 Dependências e licença** | Lockfiles, vulnerabilidades, provenance, atualização e licenças | Inventário versionado, scanner completo e política | Dependência crítica/KEV, lock ausente ou scan não enforced | Reexecutar scanner no lock exato e comprovar política aplicada |
| **MOD-007 CI/CD endurecido** | Permissões mínimas, actions pinadas, secrets, eventos, ambientes e approvals | Workflow parseado e configurações remotas quando autorizadas | Permissão ampla, ref mutável, secret em evento não confiável | Workflow negativo deve falhar e permissões devem ser verificadas |
| **MOD-008 Artefatos e releases** | Build reproduzível, checksum, assinatura/attestation, provenance e publicação | Manifest, hashes, attestation e identidade do artefato | Artefato sem vínculo ao commit ou checksum não validado | Baixar artefato imutável e verificar hash/provenance anonimamente quando público |
| **MOD-009 IaC e containers** | IaC validate/plan, policy-as-code, imagens, usuário, capabilities e scan | Arquivos parseados, plano/scans autorizados e digest da imagem | Misconfiguration crítica, imagem mutável ou privilégio excessivo | Fixture/plan negativo bloqueado e imagem por digest aprovada |
| **MOD-010 Aplicação/API** | AuthN/AuthZ, validação de entrada, TLS/CORS, rate limits, DAST e contrato API | Código/config + testes autorizados; DAST somente em alvo aprovado | Controle ausente, teste de autorização falha ou alvo não autorizado | Testes negativos por identidade/entrada e DAST sandbox autorizado |
| **MOD-011 Observabilidade e resposta** | Logs sem segredos, métricas, alertas, tracing, retenção, runbooks e recuperação | Config, alerta testável, runbook e evidência de exercício | Falha crítica invisível ou resposta sem owner/runbook | Injetar evento sintético autorizado e comprovar alerta/roteamento |
| **MOD-012 Auditoria e melhoria** | Histórico dos gates, findings, SLA, exceções, drift e reavaliação | Relatórios versionados, timestamps, owners e eventos | Evidência stale, finding sem SLA ou exceção permanente | Nova execução no snapshot corrigido deve fechar finding com evidência |

## Regras comuns

- `PASS` exige evidência não vazia e atual; para gates obrigatórios, `AUTOMATED_ENFORCED`.
- `N/A` exige prova concreta de não aplicabilidade e nunca substitui um gate obrigatório pelo perfil de risco.
- Checks remotos sem acesso autorizado são `BLOCKED`, não presumidos.
- Comandos do repositório não são confiáveis; só podem ser descritos ou executados em sandbox read-only por um runner explicitamente autorizado.
- A correção deve indicar alvo, ação, aceite e procedimento futuro, mas o investigador nunca a aplica.