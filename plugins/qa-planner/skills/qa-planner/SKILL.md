---
name: qa-planner
description: Planeja QA para um repositório e branch: analisa requisitos, define estratégia e cria cenários rastreáveis em QA.md, sem executar testes. Use antes de delegar a execução dos testes para outra IA.
argument-hint: "[branch=<branch>] [base=<branch>] [source=<PR|issue|spec>] [output=<path>] [include_worktree=true|false]"
---

# QA Planner — plano de testes, sem execução

Use esta skill para criar um **plano de QA executável por outra IA** para a branch atualmente aberta em um repositório local.

O contrato é estritamente **plan-only**:

```text
validar escopo → analisar requisitos → planejar testes → criar cenários → gravar QA.md → STOP
```

## Contrato não negociável

- Realize somente estas etapas: **1. análise de requisitos**, **2. planejamento dos testes** e **3. criação dos cenários**.
- O artefato principal é `QA.md`; ele descreve testes a executar, não resultados.
- Nunca execute testes, builds, linters, typecheckers, instalação de dependências, migrações ou chamadas de produção.
- Nunca altere código de produto, configuração, testes existentes, lockfiles, branches, commits, PRs ou issues.
- A única escrita permitida no repositório-alvo é o bloco gerenciado de `QA.md` escolhido por esta skill.
- Não invente requisito, comando, ambiente, dado de teste ou resultado. Marque inferências e lacunas explicitamente.
- A IA executora é outro workflow: ela registra resultados em `QA-RESULTS.md`, sem alterar os cenários planejados.
- Ao terminar, pare. Não inicie execução de teste, não gere `QA-RESULTS.md` e não proponha uma correção.

O marcador terminal obrigatório é:

```text
Planejamento de QA encerrado. Nenhum teste foi executado.
```

## Entrada e proteção de branch

Use o diretório de trabalho atual. Primeiro descubra a raiz com `git rev-parse --show-toplevel` e registre:

- repositório e caminho da raiz;
- branch atual e `HEAD` SHA;
- estado limpo/sujo;
- `base` e intervalo de diff usados.

| Parâmetro | Regra |
|---|---|
| `branch` | Branch esperada. Se informada e diferente da atual, pare como `BLOCKED`; nunca faça checkout, stash ou reset. |
| `base` | Base explícita. Se ausente, escolha nesta ordem: base da PR disponível localmente, `origin/HEAD`, `main`, `master`. Registre a escolha. |
| `source` | PR, issue, documento ou requisito fornecido pelo usuário. Cite-o como evidência. |
| `output` | Caminho explícito para `QA.md`; prevalece sobre a seleção automática. |
| `include_worktree` | Padrão `false`. Com `false`, planeje o `HEAD` commitado e registre alterações locais como não cobertas. Com `true`, inclua a sujeira atual, sem modificá-la. |

Se a base não puder ser identificada, se `HEAD` não puder ser resolvido ou se o diretório não for um repositório Git, emita `BLOCKED` e não crie um plano que finja cobrir uma branch.

## Evidências e autoridade

Colete somente por leitura. Priorize as fontes nesta ordem:

1. requisito, issue, PR ou especificação fornecidos em `source`;
2. instruções do repositório (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, constituição e documentos de arquitetura);
3. diff entre a base e o `HEAD`, incluindo arquivos adicionados/removidos;
4. commits, README, manifests, CI e testes existentes;
5. inferência do código — identificada como **inferida**, nunca apresentada como requisito confirmado.

Liste no plano cada evidência com caminho/URL e, quando aplicável, linhas, commit ou range de diff. Se houver contradição, preserve as duas fontes e registre uma pergunta aberta.

## Seleção do local de `QA.md`

1. `output` explícito vence, desde que esteja dentro da raiz do repositório.
2. Defina o **escopo de lifecycle**:
   - use um pacote de monorepo somente se todo o diff estiver nele **e** o pacote possuir manifest/configuração de testes próprios;
   - caso contrário, use a raiz do repositório.
3. No escopo selecionado, se já existir um diretório explícito de QA/testing com conteúdo (`docs/qa/` ou `docs/testing/`), grave `QA.md` nele.
4. Caso contrário, grave `<escopo>/QA.md`.
5. Nunca escolha diretórios gerados, de dependências, vendor, build, cache ou `.git`.
6. Registre no documento o caminho e a justificativa da escolha.

### Preservação de conteúdo humano

O bloco gerenciado usa exatamente:

```markdown
<!-- qa-planner:start -->
...
<!-- qa-planner:end -->
```

- Se o arquivo não existir, crie-o com esse bloco.
- Se ambos os marcadores existirem uma vez, atualize somente o conteúdo entre eles.
- Se existir `QA.md` sem os marcadores, ou marcadores duplicados/invertidos, pare como `BLOCKED`. Nunca sobrescreva conteúdo humano.

## Fase 1 — Análise de requisitos

Produza em `QA.md`:

- requisitos confirmados e inferidos, com IDs `REQ-001`, `REQ-002`...;
- critérios de aceite observáveis;
- áreas e contratos alterados;
- integrações, permissões, estados e migrações relevantes;
- riscos de regressão;
- ambiguidades, dependências e bloqueios.

Para cada requisito, indique `confirmado` ou `inferido` e cite evidência. Se não houver requisito explícito, use o diff como hipótese de comportamento, mas mantenha o status do plano como `PARTIAL` até que as lacunas sejam resolvidas.

## Fase 2 — Planejamento dos testes

Defina uma estratégia proporcional ao risco, com:

- escopo e fora de escopo;
- matriz de risco (`probabilidade`, `impacto`, `prioridade`);
- níveis aplicáveis: unitário, integração, API, UI/E2E, smoke, regressão, segurança, desempenho e acessibilidade;
- ambiente, massa de dados, contas, feature flags e dependências necessárias;
- comandos ou harnesses **somente quando encontrados nas evidências**; caso contrário, escreva `TBD — não encontrado`;
- critérios de entrada e de saída para a futura execução.

| Prioridade | Uso |
|---|---|
| `P0` | segurança, dinheiro, identidade, dados, indisponibilidade ou fluxo central bloqueado |
| `P1` | regra relevante, integração ou regressão provável |
| `P2` | borda, usabilidade, compatibilidade ou melhoria não bloqueadora |

## Fase 3 — Criação dos cenários

Crie cenários únicos `QA-001`, `QA-002`... Todo cenário precisa mapear ao menos um `REQ-*` ou um risco explícito. Cubra, quando aplicável:

- caminho feliz;
- entradas inválidas e estados de erro;
- limites e ausência de dados;
- autorização e isolamento entre usuários/tenants;
- falha de integrações, timeout, retry e idempotência;
- persistência, rollback e regressão;
- observabilidade e mensagens de erro;
- segurança, desempenho ou acessibilidade conforme o risco.

Use este formato por cenário:

````markdown
### QA-001 — <título objetivo>

- **Rastreabilidade:** REQ-001; RISK-002
- **Prioridade:** P0 | P1 | P2
- **Nível/tipo:** API | integração | unitário | UI/E2E | segurança | ...
- **Automação:** recomendada | manual justificadamente | TBD
- **Status inicial:** NOT_RUN
- **Pré-condições e dados:** <estado verificável>
- **Passos:**
  1. ...
- **Resultado esperado:** <resultado observável>
- **Evidência a coletar:** <assertion, log, response, screenshot ou métrica>
- **Comando/harness candidato:** <somente se comprovado; caso contrário TBD>
````

Não escreva `PASS`, `FAIL`, `SKIPPED` ou resultado executado em `QA.md`.

## Estrutura obrigatória de `QA.md`

Use os headings abaixo, nesta ordem:

```markdown
# QA Plan

<!-- qa-planner:start -->
## 1. Identificação
## 2. Evidências consultadas
## 3. Requisitos e critérios de aceite
## 4. Rastreabilidade
## 5. Escopo e fora de escopo
## 6. Estratégia de testes
## 7. Ambiente, dados e dependências
## 8. Cenários detalhados
## 9. Regressão necessária
## 10. Candidatos à automação
## 11. Dúvidas, suposições e bloqueios
## 12. Handoff para a IA executora
<!-- qa-planner:end -->
```

Em `## 1. Identificação`, registre `READY`, `PARTIAL` ou `BLOCKED`, a branch/base/SHAs, o range de diff, o local escolhido e a justificativa.

Em `## 12. Handoff para a IA executora`, instrua a próxima IA a:

1. validar que branch e `HEAD` ainda coincidem com o plano;
2. executar somente cenários `QA-*` aplicáveis;
3. registrar comandos, entradas, saída real, evidências e timestamps;
4. gravar resultados em `QA-RESULTS.md`, preservando `QA.md` como plano;
5. usar apenas `PASS`, `FAIL`, `BLOCKED` ou `SKIPPED` em `QA-RESULTS.md`;
6. não inventar resultado quando ambiente, dado ou dependência estiver indisponível.

O documento deve terminar, antes do marcador de fechamento, com:

```text
Planejamento de QA encerrado. Nenhum teste foi executado.
```

## Verificação final

Antes de concluir:

- confirme que somente `QA.md` foi criado ou alterado no repositório-alvo;
- confirme que os marcadores e os 12 headings existem uma vez e estão ordenados;
- confirme que todo cenário tem rastreabilidade, prioridade, pré-condição, passos, resultado e evidência;
- confirme que cada comando candidato tem fonte ou está `TBD`;
- confirme que não há resultado de execução em `QA.md`;
- confirme que toda incerteza permanece explícita;
- encerre no marcador obrigatório e pare.
