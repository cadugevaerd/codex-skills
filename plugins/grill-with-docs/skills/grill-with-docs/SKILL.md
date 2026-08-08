---
name: grill-with-docs
description: Entrevista decisões arquiteturais por work item isolado, mantém feature plan-only e oferece hotfix-fast executável com HOTFIX-GO fail-closed.
argument-hint: "iniciar|retomar|pausar|auditar|conciliar|migrar|status|checkpoint <git-root>"
---
# Grill with Docs v2.4.0

Protocolo **plan-only** para uma feature, fix ou hotfix em worktree/branch dedicada. Cada trabalho possui identidade e artefatos próprios; o estado global é somente uma projeção de trabalhos concluídos.

```text
worktree A ──> .grill/work-items/<work-id-A>/ ─┐
worktree B ──> .grill/work-items/<work-id-B>/ ─┼─> reconcile ─> .grill/global/
worktree C ──> .grill/work-items/<work-id-C>/ ─┘
```

## Regras invioláveis

1. Nunca grave artefatos decisórios no root legado durante um trabalho novo.
2. Nunca escreva no diretório de outro `work_id`.
3. `WORKFLOW.md` e `.specify/memory/constitution.md` são project-wide.
4. A Constituição é opcional. Ausente significa `not-present`; presente é read-only e norma máxima.
5. Nenhum ADR, decisão local ou reconciliação pode dispensar, enfraquecer ou violar a Constituição.
6. Hooks são read-only e nunca criam work items automaticamente.
7. Hotfix-fast é uma exceção operacional fechada: exige escopo, reprodução/evidência, teste de correção, rollback e evidência constitucional; não depende de ROADMAP, BL, DQ ou reconciliação para ser seguro.
8. Feature e fix permanecem plan-only; hotfix só entrega HOTFIX-GO para ship externo e reconciliação/auditoria documental completa são pós-ship.
7. A sessão termina em `PLAN_ONLY_STOP`; não implementa código, não executa `specify|plan` e não faz commit/merge.

## Identidade e inicialização

Resolva o Git root real e trabalhe em branch/worktree dedicada. Materialize ou valide o workflow project-wide:

```text
python3 "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/grill-with-docs/scripts/ensure_workflow.py" --ensure ROOT
```

Crie o namespace isolado:

```text
python3 "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/grill-with-docs/scripts/grill_workspace.py" \
  init ROOT --type feature|fix|hotfix --slug SLUG [--work-id WORK_ID] [--base-ref REF]
```

Sem `--work-id`, o core gera uma identidade collision-resistant. `--work-id` explícito serve para retomada/idempotência e deve corresponder à mesma identidade. A criação usa lock, staging e rename atômico; colisão ou integridade divergente bloqueiam.

`WORK-ITEM.json` registra metadata imutável e hash canônico: `work_id`, tipo, slug, branch, HEAD, base ref/commit, Constituição e workflow. Escopo, dependências e conflitos ADR permanecem declarados em campos próprios para reconciliação.

## Entradas da entrevista

Defina `WORK_ITEM=.grill/work-items/<work-id>`. As oito entradas decisórias são:

1. `.specify/memory/constitution.md` — project-wide, opcional e read-only;
2. `WORKFLOW.md` — project-wide;
3. `$WORK_ITEM/CONTEXT.md`;
4. `$WORK_ITEM/docs/adr/`;
5. `$WORK_ITEM/ROADMAP.md`;
6. `$WORK_ITEM/DECISION-BACKLOG.md`;
7. `$WORK_ITEM/PLAN-CONTEXT.md`;
8. `$WORK_ITEM/handoffs/FASE-NNN-SPECIFY-HANDOFF.md` selecionado.

Arquivos de controle, fora da lista de oito entradas: `WORK-ITEM.json`, `CONSTITUTION-CHECK.md`, `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl`, `state.json` e `AUDIT.md`.

- `CONTEXT.md`: somente glossário e linguagem ubíqua.
- `docs/adr/`: decisões difíceis de reverter e trade-offs reais.
- `ROADMAP.md`: fases, ordem explícita, dependências, estado e handoff.
- `DECISION-BACKLOG.md`: decisões adiadas com owner, evidência e gatilho.
- `PLAN-CONTEXT.md`: HOW técnico cumulativo para planejamento.
- Handoff: somente WHAT/WHY da fase selecionada.

## Gate constitucional

Se não existir Constituição, registre `not-present` sem inventar princípios. Se existir:

1. leia somente `.specify/memory/constitution.md` em UTF-8;
2. registre SHA-256 no metadata e em `CONSTITUTION-CHECK.md`;
3. mapeie exatamente cada cláusula normativa H2/H3;
4. registre `id`, `heading`, `status`, `evidence` e `justification`;
5. aceite somente `PASS` ou `NOT-APPLICABLE`, ambos com evidência e justificativa.

Cobertura ausente/duplicada, status desconhecido, `PENDING`, `UNMAPPED`, `BLOCKED`, `VIOLATION`, placeholder, ambiguidade ou hash stale terminam em `BLOCKED-CONSTITUTION` (exit `3`). Se a Constituição aparecer ou mudar, revalide todo o work item. Não há waiver constitucional.

## Entrevista incremental

```text
INIT → MAP_FRONTIER → ASK_ONE → RECORD → RECOMPUTE_FRONTIER
                         ↑                    │
                         └──── decisões ──────┘
                                              ↓
                 COMPLETE | BLOCKED | SAFETY_STOP | PAUSED_USER
```

1. Classifique o cenário e registre fontes oficiais ou `EVIDENCE GAP`.
2. Carregue a fronteira inteira e selecione uma DQ material com dependências satisfeitas.
3. Faça exatamente uma pergunta atômica com evidência, recomendação, opções e custos.
4. Registre `resolved`, `deferred`, `split`, `blocked` ou `out-of-scope`.
5. Faça impact scan e atualize somente o `$WORK_ITEM` atual.
6. Acrescente uma linha JSON ao `ROUND-LOG.jsonl` e recalcule a fronteira.

Mesmo fingerprint admite no máximo duas perguntas sem evidência nova. Duas rodadas sem progresso, três expansões consecutivas ou 25 perguntas materiais exigem checkpoint e `SAFETY_STOP`. `pausar|stop` grava `PAUSED_USER`. Contradições nunca são sobrescritas.

IDs `ADR-NNNN`, `DQ-NNNN`, `BL-NNNN`, `FASE-NNN` e `R-NNNN` são locais ao work item. Na projeção global tornam-se `<work-id>/<ID>`.

## Auditoria read-only

```text
python3 "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/grill-with-docs/scripts/grill_workspace.py" \
  audit ROOT --work-id WORK_ID
```

Para artefatos externos ao checkout, use `--artifact-root PATH --project-root ROOT`. A auditoria valida a Constituição e chama o auditor decisório real com roots separados. Ela não chama `ensure_workflow.py`, não cria arquivos e compara fingerprints antes/depois.

Exit codes: `0 GO/MILESTONE-COMPLETE`, `1 NO-GO`, `2 BLOCKED/uso`, `3 BLOCKED-CONSTITUTION`.

## Reconciliação global

Preview é o padrão e não escreve:

```text
python3 .../grill_workspace.py hotfix ROOT --slug SLUG --scope PATHS --reproduction REPRO --evidence EVIDENCE --correction-test TEST --rollback ROLLBACK --constitution-evidence EVIDENCE --test-command "python3 -m unittest tests/test_fix.py"
python3 .../grill_workspace.py reconcile ROOT \
  [--source-root OUTRA_WORKTREE] [--source-ref REF] [--work-id ID]
```

`--work-id ID` faz reconciliação incremental fail-closed de um único alvo: irmãos pendentes ou conflitantes não bloqueiam, mas estado, Constituição, escopo, ADRs e dependências do alvo continuam obrigatórios. Preview não escreve. Com `--apply`, a projeção é acumulada em recibos determinísticos `.grill/global/receipts/ID.json`; reaplicação idêntica retorna `REUSED`. Um global legado sem recibos bloqueia com `GLOBAL-BASELINE-UNVERIFIED` (não há migração implícita).

O reconciliador lê bundles completos sem checkout e detecta: `work_id` duplicado divergente, sobreposição de escopo, dependência ausente/cíclica, conflito ADR declarado, estado não concluído e hash constitucional stale. Só aceita milestone com `milestone_status=completed`, `state.status=complete`, `active_phase=null`, `audit_verdict=GO` e todas as fases do `execution-order` em `complete|superseded`. IDs são qualificados globalmente.

O fluxo feature/fix termina em `PLAN_ONLY_STOP`; não use `reconcile` como continuação de um hotfix antes do ship externo. Aplicação exige branch de integração explícita, árvore limpa e zero conflitos:

```text
python3 .../grill_workspace.py hotfix ROOT --slug SLUG --scope PATHS --reproduction REPRO --evidence EVIDENCE --correction-test TEST --rollback ROLLBACK --constitution-evidence EVIDENCE --test-command "python3 -m unittest tests/test_fix.py"
python3 .../grill_workspace.py reconcile ROOT --apply --integration-branch BRANCH
```

Somente `.grill/global/ROADMAP.md` e `.grill/global/AUDIT.md` são gerados. A segunda execução é byte-idêntica/no-op. A projeção global nunca reescreve work items.

## Migração legada

Sempre execute preview antes de aplicar:

```text
python3 .../grill_workspace.py migrate ROOT --type feature|fix|hotfix --slug SLUG [--work-id ID]
python3 .../grill_workspace.py migrate ROOT --type feature|fix|hotfix --slug SLUG [--work-id ID] --apply
```

A migração copia arquivos planos, `docs/adr|adrs` e `handoffs` para staging, preserva bytes e mantém a origem. Symlink, UTF-8 inválido, colisão ou divergência bloqueiam; falha não deixa bundle parcial.

## ROADMAP, GO e `PLAN_ONLY_STOP`

Hotfix-fast não lê nem altera ROADMAP/BL/DQ; sua saída é `HOTFIX-GO` somente com escopo fechado, evidência reproduzível, teste de correção, rollback e sem conflito constitucional real.

A ordem vem de `execution-order`, não dos números de fase. Para `GO`, a fase selecionada deve ser a primeira incompleta, ter predecessores terminais (`complete|superseded`), nenhum BL aberto e handoff WHAT/WHY exclusivo. `PLAN-CONTEXT.md`, ADRs e `CONTEXT.md` fornecem HOW. Quando não resta fase incompleta, o estado terminal exige zero BL/DQ material aberto, `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria emite `MILESTONE-COMPLETE`. Uma última fase `superseded` é conclusão legítima, não NO-GO por si só.

Após auditoria `GO` e entrega do handoff, emita `PLAN_ONLY_STOP` e pare. Esse stop aplica-se somente a feature/fix; hotfix encerra em `hotfix.closed` e pode seguir para `HOTFIX-GO`. Agentes externos executarão `specify|plan` em outro ciclo. Após ship, marque a fase entregue como `complete` ou a fase substituída como `superseded`; ao encerrar o milestone, grave o estado terminal, reaudite até `MILESTONE-COMPLETE` e só então reconcilie globalmente.

## Portabilidade do workspace

O core requer Python >=3.10 e não possui dependências externas. Use `uv run --no-project` preferencialmente; `python3`, `python` ou `py -3` são fallbacks. A publicação do bundle escolhe previamente a capacidade completa de rename: em POSIX usa parent aberto com `O_RDONLY|O_DIRECTORY|O_NOFOLLOW`, compara `stat`/`fstat` e chama `os.rename` com `src_dir_fd`/`dst_dir_fd`; sem isso usa caminhos completos após validar parent/source/target. O fallback recusa um destino já visível, mas não reproduz proteção contra substituição do parent ou criação concorrente do target entre validação e rename (limite TOCTOU); o lock serializa escritores cooperantes. `hotfix-go` usa a command line nativa do Windows com `shell=False`. Esta versão não altera os hooks e não declara hooks universais em Windows.
