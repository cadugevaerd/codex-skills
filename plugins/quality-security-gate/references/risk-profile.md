# Perfil de risco

O classificador usa sinais observáveis e sempre conserva o maior nível encontrado.

| Perfil | Sinais mínimos | Exigência |
|---|---|---|
| **P1** | Repositório local/documental sem sinais de aplicação, deploy, CI, container ou IaC | `GATE-001..003` |
| **P2** | Aplicação/dependências, CI/CD, container, IaC, API interna ou publicação de artefato | `GATE-001..004` |
| **P3** | Produção, API pública, IAM/autorização privilegiada, dados pessoais, pagamentos ou impacto crítico | `GATE-001..005` |

## Regras fail-closed

- Instrução ilegível, symlink, encoding inválido, mudança durante leitura ou fingerprint ambíguo bloqueiam a análise.
- Conteúdo é lido uma vez; os sinais de risco derivam dos mesmos bytes hasheados no snapshot. O relatório registra apenas os sinais, não conteúdo sensível.
- Sinal desconhecido não reduz risco. Quando a classificação não puder ser comprovada, use P3 conservador e `BLOCKED`.
- A skill não aceita downgrade de risco ou exceção nesta versão.
- A classificação seleciona gates; os investigadores comprovam eficácia e enforcement. Uma coisa não substitui a outra.