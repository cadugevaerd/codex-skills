---
name: grill-with-docs
description: Entrevista decisões arquiteturais uma por vez, converge por fronteira auditável e mantém ROADMAP por fases.
argument-hint: "iniciar|retomar|pausar|auditar <diretório>"
---
# Grill with Docs

Use este protocolo para transformar uma conversa de arquitetura em decisões rastreáveis. Trabalhe no repositório real, grave artefatos no momento da decisão e nunca chame uma afirmação de verificada sem fonte.

## Artefatos canônicos

- `CONTEXT.md`: somente glossário e linguagem ubíqua;
- `docs/adr/ADR-NNNN.md`: decisões arquiteturais;
- `DECISION-BACKLOG.md`: decisões adiadas (`BL-NNNN`);
- `ROADMAP.md`: fases entregáveis e dependências;
- `DECISION-FRONTIER.md`: decisões materiais do loop (`DQ-NNNN`);
- `ROUND-LOG.jsonl`: histórico append-only de cada rodada;
- `state.json`: checkpoint retomável;
- `handoffs/FASE-NNN-SPECIFY-HANDOFF.md`: entrada WHAT/WHY isolada de cada fase;
- `PLAN-CONTEXT.md`: decisões HOW consumíveis no planejamento técnico.

## Inicialização

1. Classifique o cenário como **brownfield**, **greenfield com autoridade externa** ou **greenfield com EVIDENCE GAP**. Em greenfield, registre título, URL, versão/data, seção e consulta da fonte oficial. Blog ou memória não substituem fonte oficial.
2. Classifique cada afirmação como `official-doc`, `code`, `test`, `existing-adr`, `user-decision` ou `inference`; use estado `verified`, `partial` ou `unverified`.
3. Crie ou retome `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl` e `state.json`. Carregue a fronteira inteira antes de fazer a próxima pergunta.
4. Uma decisão é material se pode alterar escopo, custo, prazo, arquitetura, segurança, conformidade, dependência externa, aceite ou o veredito da fase.

## Loop de decisão

```text
INIT → MAP_FRONTIER → ASK_ONE → RECORD → RECOMPUTE_FRONTIER
                         ↑                    │
                         └──── decisões ──────┘
                                              ↓
                 COMPLETE | BLOCKED | SAFETY_STOP | PAUSED_USER
```

1. Selecione a decisão `open` de maior impacto cujas dependências estejam satisfeitas.
2. Faça **exatamente uma pergunta atômica**. Apresente Evidência, Recomendação, Opções, custo de implementação/operação/reversão e a pergunta.
3. Após a resposta, grave uma transição auditável: `resolved`, `deferred`, `split`, `blocked` ou `out-of-scope`.
4. Atualize CONTEXT, ADR, BL, ROADMAP e dependências afetadas; nova evidência exige impact scan: termos → ADRs → BLs → ROADMAP → dependências.
5. Acrescente uma linha JSON válida em `ROUND-LOG.jsonl` com `round_id`, `question_id`, evidências, artefatos alterados, transição, `progress_delta`, escopo e próxima ação.
6. Recalcule a fronteira inteira. Reformular a mesma pergunta sem evidência nova **não** é progresso.

### Fronteira `DQ-NNNN`

Cada DQ registra fase, pergunta canônica, fingerprint normalizado, impacto `high|medium|low`, estado, artefatos/termos afetados, dependências e referência final para CONTEXT, ADR ou BL. Não duplique DQs para a mesma pergunta/fingerprint aberta.

### Proteções de convergência

- Mesmo fingerprint: no máximo duas perguntas sem evidência nova; na terceira ocorrência, decisão não crítica vira `deferred`, crítica vira `blocked`, ou a sessão entra em `SAFETY_STOP`.
- Ambiguidade: no máximo uma clarificação por DQ; persistindo, `BLOCKED` ou `SAFETY_STOP`, sem inventar decisão.
- Sem progresso: duas rodadas sem transição ou evidência/artefato novo resultam em `SAFETY_STOP`.
- Escopo: toda decisão fora de `scope-in` exige gate explícito; sem aprovação, vira `out-of-scope`/BL em fase futura. Três rodadas consecutivas de crescimento da fronteira exigem pausa para replanejamento.
- Budget: após 25 perguntas materiais na execução, grave checkpoint e retorne `SAFETY_STOP`; retome somente com `retomar`.
- `stop` ou `pausar` grava `PAUSED_USER`; nunca interprete pausa como saturação.
- Nunca sobrescreva ADR/BL/evidência conflitante. Abra uma DQ de resolução e impeça `GO` até ela ser resolvida ou adiada formalmente.
- Os limites vêm de `state.json`/configuração no início da sessão e não podem ser ampliados implicitamente pelo modelo.

## ROADMAP por fases

Em projeto com ROADMAP legado, migre cada etapa para `FASE-NNN` antes de buscar `GO`; o auditor rejeita headings não fase. Crie `ROADMAP.md` ao haver sequenciamento, dependência, bloqueio ou mais de uma entrega. Use somente fases `FASE-NNN`:

```markdown
## FASE-001 — Nome
- state: ready-for-specify
- objetivo: resultado da fase
- scope-in: incluído
- scope-out: excluído
- context-refs: Termo Canônico
- ADRs: ADR-0001
- BLs: BL-0001
- depends-on: none
- entrada: critério
- saída: critério
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
```

Regras:

- `context-refs` contém termos existentes em `CONTEXT.md`;
- `ADRs` lista somente decisões tocadas; se `none`, declare `ADRs-justificativa`;
- `scope-in`/`scope-out` impedem expansão silenciosa;
- dependências referenciam IDs `FASE-NNN` e formam DAG;
- cada fase tem handoff exclusivo;
- apenas `state: ready-for-specify` + auditoria `GO` pode alimentar `speckit.specify`;
- entregue ao `specify` somente o handoff da fase selecionada, nunca o ROADMAP inteiro.

## Registro de decisão

- Se ADR foi solicitado, registre cada decisão substantiva ao fechar. Caso contrário, crie ADR somente quando for difícil de reverter, surpreendente sem contexto e houver trade-off real.
- ADR gerenciado vive em `docs/adr/`, usa `managed-by: grill-with-docs/v1`, status `proposed|conditional|accepted|superseded|deprecated`, evidência e fontes. `accepted` não depende silenciosamente de `unverified`; use `conditional` e `BL-NNNN`.
- Adiamento exige motivo, impacto, evidência necessária, responsável, gatilho de retomada e ponto de parada.
- Emenda, exceção e substituição são uma ação única: atualize ADR antigo/novo, backlinks, CONTEXT, backlog, ROADMAP, fronteira e auditoria. Substituição deixa o antigo `superseded` e nunca dois `accepted` conflitantes.

## Auditoria, término e handoff

Audite a cada cinco ADRs novos/alterados, após pivô/emenda/exceção/substituição, antes de selecionar uma fase e no encerramento:

```text
python3 scripts/audit_decisions.py DIRETÓRIO
```

O auditor é fail-closed para artefatos gerenciados e ignora ADRs legados sem `managed-by: grill-with-docs/v1`.

- `COMPLETE + GO`: não há DQ material `open|blocked`; decisões estão resolvidas/deferidas/split/out-of-scope com referências válidas; auditoria `GO`; segunda passada não cria DQ média/alta; somente este caso libera handoff.
- `COMPLETE + NO-GO`: conclusão negativa explícita e auditada; não libera handoff.
- `BLOCKED`: decisão crítica depende de evidência/aprovação externa; registre owner, próxima ação, escalonamento e impacto no ROADMAP.
- `SAFETY_STOP` e `PAUSED_USER`: checkpoint retomável; nunca são `GO` ou handoff pronto.

Relate escopo, contagens, fronteira, estados `resolved/deferred/blocked`, achados e veredito `GO`, `NO-GO` ou `BLOCKED`.
