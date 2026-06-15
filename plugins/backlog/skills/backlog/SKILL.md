---
name: "backlog"
description: "Registrar, triar e promover itens diferidos (features, bugs, débitos técnicos, chores) na fonte da verdade .specify/backlog.json do projeto atual. Use quando identificar trabalho que não será feito agora, quando for revisar/promover/resolver o backlog, quando houver TODOs/FIXMEs soltos ou listas de pendências fora da fonte da verdade, ou quando o projeto ainda não tiver a estrutura de backlog (a skill faz bootstrap e migra backlog não estruturado)."
argument-hint: "add | list | format | promote | resolve | discard | init <texto livre do que fazer>"
metadata:
  author: "civilmaster"
  source: "originada no projeto masterai-agents-backend; promovida a skill global"
user-invocable: true
disable-model-invocation: false
---

# Skill: backlog

Opera a **fonte da verdade dos itens diferidos** do projeto atual (raiz do
repositório em que a sessão está rodando).

## Bootstrap — quando a estrutura base não existe

**Antes de qualquer operação**, verifique se a estrutura base existe na raiz do
projeto: `.specify/backlog.json`, `BACKLOG.md` e a seção `## Fonte da Verdade de
Backlog` no `AGENTS.md` (ou `CLAUDE.md` em projetos herdados). Se **qualquer peça faltar** (ou via comando explícito
`init`), complemente **só o que falta** — não pergunte, crie e informe o que foi
criado. Nunca sobrescreva o que já existe:

1. **`.specify/backlog.json`** — skeleton (substituir `<projeto>` pelo nome do
   diretório/repo e `<hoje>` pela data atual):

   ```json
   {
     "_about": "Fonte da verdade dos itens diferidos (features, bugs, débitos técnicos) do <projeto>. NÃO é roadmap nem spec — é o registro de 'quando der, faz'. Como usar: skill global /backlog. Ponteiro legível: BACKLOG.md (raiz). Instrução normativa: AGENTS.md, seção 'Fonte da Verdade de Backlog'.",
     "version": 1,
     "updated": "<hoje>",
     "next_id": 1,
     "enums": {
       "type": ["feature", "bug", "debt", "chore"],
       "status": ["aberto", "em-andamento", "promovido", "resolvido", "descartado"],
       "priority": ["critica", "alta", "media", "baixa"]
     },
     "items": []
   }
   ```

2. **`BACKLOG.md`** (raiz) — ponteiro legível:

   ```markdown
   # Backlog — itens diferidos

   > **Fonte da verdade:** [`.specify/backlog.json`](.specify/backlog.json).
   > Este arquivo é só um ponteiro legível — **não registre itens aqui**, edite o JSON.

   Registro único de **features, bugs e débitos técnicos** que não serão resolvidos
   agora ("quando der, faz"). Não é roadmap, não é spec. Cada item tem um id
   `BL-NNNN`, um `type`, um `status` e — quando precisa de detalhe longo — um
   arquivo em `docs/backlog/<id>-*.md`.

   ## Como usar

   - **Ver / triar:** abra `.specify/backlog.json` (campo `items`).
   - **Adicionar, atualizar, promover ou resolver item:** use a skill global
     **`/backlog`** — ela gera o próximo `BL-NNNN`, valida os enums e mantém
     `next_id`/`updated`.

   > O glossário canônico dos enums vive no próprio JSON (chave `enums`).
   ```

3. **`AGENTS.md`** do projeto — se existir e **não** tiver a seção
   `## Fonte da Verdade de Backlog`, adicionar a seção abaixo (ao final ou junto
   das demais regras de processo); se `AGENTS.md` não existir, mas `CLAUDE.md`
   existir, adicione a seção em `CLAUDE.md` sem duplicar instruções. Se nenhum
   deles existir, crie `AGENTS.md` contendo só essa seção:

   ```markdown
   ## Fonte da Verdade de Backlog (itens diferidos)

   Toda **feature, bug ou débito técnico que NÃO vai ser resolvido agora** MUST ser
   registrado na fonte da verdade única: **`.specify/backlog.json`**. Não deixe
   trabalho diferido morrer em TODO solto no código ou em observação de sessão.

   - **Fonte da verdade:** `.specify/backlog.json` (estruturado, único). Cada item é
     `BL-NNNN` com `type` (feature | bug | debt | chore), `status`, `priority`
     (severidade: critica | alta | media | baixa), `rank` (1–100, ordem de ataque),
     `agent`, `source`, `related`, `promoted_to` e `notes`. Detalhe longo vai em
     `docs/backlog/<id>-*.md`, apontado pelo campo `detail`.
   - **Ponteiro legível:** `BACKLOG.md` (raiz) — só explica o sistema, **não** lista
     itens (a lista vive só no JSON, para não duplicar).
   - **Como operar:** use a skill global **`/backlog`** para adicionar, listar,
     promover ou resolver itens — ela gera o próximo id, valida enums e mantém
     `next_id`/`updated`. Para reorganizar (re-triar severidade + atribuir o `rank`
     de ordem de ataque), use **`/backlog format`**.
   ```

4. Confirmar ao usuário o que foi criado e **seguir com a operação pedida**
   (ex: se o pedido era `add`, registrar o item logo após o bootstrap).

> Se o projeto usa enums próprios (outros `status`/`type`), respeite os que já
> estão no JSON existente — o skeleton acima é só para criação do zero.

> **Upgrade aditivo do enum `priority` (idempotente).** Em **toda** execução, se o
> `enums.priority` do JSON existente não contém `"critica"`, adicione-o (no topo:
> `["critica", "alta", "media", "baixa"]`). É **aditivo e não-destrutivo** — não
> reclassifica nenhum item, só disponibiliza o nível. Mantém todos os projetos
> consistentes com a severidade de 4 níveis. Faz parte do "complemente só o que
> falta" do bootstrap; não pergunte, faça e informe.

## Varredura — backlog não estruturado (toda execução)

Em **toda** invocação, após o bootstrap e ANTES da operação pedida, varra o
projeto por trabalho diferido que vive fora da fonte da verdade:

1. **Código:** grep por `TODO`, `FIXME`, `XXX`, `HACK` — excluindo diretórios de
   dependências/artefatos (`.git`, `node_modules`, `.venv`, `venv`, `vendor`,
   `dist`, `build`, `__pycache__`, `.claude/worktrees`, `.codex/worktrees`, arquivos lock) e
   marcadores que já referenciam um id (`BL-NNNN`).
2. **Notas:** arquivos tipo `TODO.md`, `NOTES.md`, `PENDENCIAS.md` e seções
   "Backlog"/"Pendências"/"TODO" em markdowns de docs. `BACKLOG.md` listando
   itens = violação (itens vivem só no JSON) — migrar a lista.
3. **Classificar cada achado:**
   - **Trabalho diferido real** (feature/bug/débito/chore que não será feito
     agora) → **migrar**: criar item `BL-NNNN` com `source` =
     `"varredura /backlog — <path>:<linha>"`, e substituir o original por
     referência: comentário de código vira `TODO(BL-NNNN): <resumo de 1 linha>`;
     lista em markdown é removida e o arquivo ganha um ponteiro para
     `.specify/backlog.json` (se o arquivo ficar vazio/sem propósito, removê-lo).
   - **Trivial/local** (nota de implementação imediata, contexto da própria
     linha de código) → deixar como está, não é backlog.
   - **Ambíguo** → não migrar em silêncio: listar ao usuário como candidato,
     com path:linha e o porquê da dúvida.
4. **Reportar ao final da operação:** itens migrados (`BL-NNNN ← path:linha`) e
   candidatos ambíguos. Se a varredura não achar nada, não reporte nada.

**Idempotência:** `TODO(BL-NNNN)` no código não gera item novo; antes de criar,
cheque duplicata por `title`/`related` contra os itens existentes (inclusive
`resolvido`/`descartado`). Se houver dezenas de achados, migre só os claros e
liste o resto como candidatos — a varredura não pode transformar a invocação
numa sessão de migração que o usuário não pediu.

## Fonte da verdade

`/.specify/backlog.json` é o **único** registro canônico. Estrutura:

```jsonc
{
  "version": 1,
  "updated": "YYYY-MM-DD",   // data da última edição do arquivo
  "next_id": <int>,          // próximo número livre p/ BL-NNNN
  "enums": { "type": [...], "status": [...], "priority": [...] },
  "items": [ { /* item */ } ]
}
```

Cada item:

| campo | tipo | regra |
|---|---|---|
| `id` | string | `BL-NNNN` (zero-padded, 4 dígitos). Nunca reusar id. |
| `type` | enum | `feature` \| `bug` \| `debt` \| `chore`. feature/bug = produto; debt = dívida técnica; chore = processo/docs/infra. |
| `title` | string | uma linha, no infinitivo quando for ação. |
| `status` | enum | `aberto` \| `em-andamento` \| `promovido` \| `resolvido` \| `descartado`. |
| `priority` | enum | `critica` \| `alta` \| `media` \| `baixa`. Severidade — ver "Severidade & rank". |
| `rank` | int\|null | 1–100, **único** no backlog, maior = mais importante. Atribuído **só** pela operação `format` (re-rank). `null` fora do universo do rank (status ≠ `aberto`/`em-andamento`). |
| `agent` | string\|null | módulo/runtime/área afetada, ou `null` se transversal/infra. |
| `created` | date | data de captura (não muda). |
| `updated` | date | última mudança no item. |
| `source` | string | de onde nasceu (grilling, bug em prod, e-mail…). |
| `detail` | string\|null | path de `docs/backlog/<id>-*.md` quando há detalhe longo; senão `null`. |
| `related` | string[] | paths de código, specs, ADRs, princípios. |
| `promoted_to` | string\|null | link da spec/bugfix quando `status=promovido`. |
| `notes` | string | contexto curto: o que fazer, esforço, restrições. |

**Ponteiro legível:** `BACKLOG.md` (raiz) explica o sistema mas **não** lista itens
— não edite a lista lá. **Instrução normativa:** `AGENTS.md` do projeto, seção
"Fonte da Verdade de Backlog" (ou `CLAUDE.md` em projetos herdados).

## Severidade & rank

Dois eixos descrevem a urgência de um item: a **severidade** (campo `priority`,
qualitativo) e o **rank** (campo `rank`, quantitativo, atribuído só pela operação
`format`).

**Severidade (`priority`) — 4 níveis:**

| nível | significado |
|---|---|
| `critica` | Precisa implementar **antes de qualquer coisa**. Bloqueia o resto. |
| `alta` | Pode-se fazer outras coisas, mas é recomendado **parar assim que puder** para implementar. |
| `media` | Não é obrigatório, mas **deixa o código melhor** quando feito. |
| `baixa` | Apenas **estético** / cosmético. |

**Rank (`rank`) — score 1–100 com faixas por severidade.** É um número **único** em
todo o backlog (sem repetição), maior = mais importante, que responde "dentro de uma
mesma severidade, qual atacar primeiro" e dá uma **ordem de ataque única** no projeto
inteiro. Cada severidade ocupa uma faixa contígua do 1–100:

| severidade | faixa | slots |
|---|---|---|
| `critica` | 76–100 | 25 |
| `alta` | 51–75 | 25 |
| `media` | 26–50 | 25 |
| `baixa` | 1–25 | 25 |

O rank **só** é (re)calculado pela operação `format` (ver abaixo). Fora dela — no
`add`, `promote`, `resolve`, `discard` — o `rank` não é inventado: nasce `null` e só
é preenchido/limpo pelas regras descritas em cada operação.

## Operações

Determine a operação pelo argumento (`add`/`list`/`format`/`promote`/`resolve`/
`discard`/`init`) ou pelo texto livre. Sempre **leia o JSON antes de editar** e
**reescreva o arquivo inteiro válido** (sem comentários — JSON puro).

### add — registrar item novo

1. Ler `.specify/backlog.json`.
2. `id = "BL-" + zero_pad(next_id, 4)`.
3. Preencher os campos. Mínimos obrigatórios: `id`, `type`, `title`, `status`
   (`aberto`), `priority`, `created` (hoje), `updated` (hoje), `source`. Os demais
   podem ser `null`/`[]`/`""` se desconhecidos — mas tente preencher `agent`,
   `related` e `notes`. O `rank` nasce `null` — só a operação `format` o atribui.
4. Se o item tem detalhe longo (esboço de código, decisões de grilling, esboço de
   spec), criar `docs/backlog/<id>-<slug>.md` com um header apontando o id +
   `.specify/backlog.json`, e setar `detail` para esse path.
5. `next_id += 1`; `updated` (topo) = hoje; `items.push(item)`.
6. Confirmar ao usuário: id atribuído + resumo.

> Antes de criar, **cheque duplicatas** por `title`/`related` — se já existe item
> equivalente, atualize-o em vez de duplicar.

### list — triar (read-only)

`list` é **read-only**: lê o JSON e exibe, **nunca muta** o arquivo nem calcula
rank. Apresenta uma tabela (id · type · title · status · priority · rank · agent).
Suporte filtros do texto livre: por `status` (default: esconder
`resolvido`/`descartado`), por `agent`, por `type`, por `priority`. Ordenar por
priority (`critica`→`alta`→`media`→`baixa`), depois por `rank` desc (itens sem
rank por último), depois por id.

> Para reorganizar o backlog (re-triar severidade + atribuir o `rank` de "ordem de
> ataque"), use a operação **`format`** — que muta o JSON. `list` só mostra o estado
> atual.

### format — reorganizar (re-triar severidade + atribuir rank)

`format` é a operação que **reorganiza o backlog inteiro**: re-avalia a severidade
(`priority`) de cada item de trabalho ativo e atribui o `rank` 1–100 (ordem de
ataque única). Diferente de `list` (read-only), `format` **muta** o JSON — mas só
**após confirmação** do usuário.

**Universo:** apenas itens com `status` ∈ {`aberto`, `em-andamento`}. Itens
`promovido`/`resolvido`/`descartado` ficam **fora** — seu `rank` é forçado a `null`
(não estão na fila de ataque).

Passos:

1. **Ler** `.specify/backlog.json` e aplicar o upgrade aditivo do enum `priority`
   (adicionar `"critica"` se faltar — ver bootstrap).
2. **Coletar** os itens do universo (aberto/em-andamento).
3. **Re-triar a severidade** de cada item conforme as definições da seção
   "Severidade & rank" (crítica = antes de tudo · alta = pare assim que puder ·
   média = melhora o código · baixa = estético), usando o julgamento a partir de
   `type`, `notes`, `related`, `source`. Isso **pode mudar** o `priority` de um item
   (ex: `alta`→`critica`).
4. **Ordenar dentro de cada faixa de severidade** por **impacto + bloqueio
   primeiro**: sobe quem tem maior impacto e/ou destrava outros itens (dependência);
   empate quebrado por **menor esforço** (quick win). Inferir de `notes`/`type`/
   `related`/`source`.
5. **Atribuir o `rank`** mapeando cada faixa ao seu intervalo (crítica 76–100, alta
   51–75, média 26–50, baixa 1–25): o item no topo da faixa recebe o maior número
   disponível da faixa e os demais descem. Números **distintos** em todo o backlog,
   nunca repetidos. Pode deixar gaps dentro da faixa para expressar "quão mais
   importante", desde que **não saia da faixa** nem repita número.
6. **Saturação (fail-loud).** Se uma faixa tiver **mais itens ativos que slots**
   (ex: 30 críticas para 25 números em 76–100), **PARE** — não atribua número
   repetido nem invada a faixa vizinha. Reporte a faixa saturada e peça re-triagem
   ao usuário (rebaixar alguns de severidade, resolver/descartar, ou quebrar itens).
   A invariante "sem repetição" é inegociável.
7. **Gate de confirmação.** Apresente a **proposta** como a view agrupada (formato
   abaixo), **destacando as mudanças de severidade** (ex: `BL-0007 alta→critica`) e
   os ranks atribuídos. **Só grave após o OK** do usuário.
8. **Gravar.** Para cada item alterado: setar `priority` (se mudou) e `rank`,
   atualizar `updated` = hoje. Garantir `rank=null` em todo item fora do universo.
   Atualizar `updated` do topo. Reescrever o JSON inteiro válido.

**Saída — view agrupada (box-drawing).** Um cabeçalho por severidade (label +
faixa + descrição) e, abaixo, uma tabela box-drawing (`━` no header, `─` entre
linhas) com colunas `rank | id | title | type | agent`, ordenada por `rank` desc.
Grupos sem itens são omitidos. Exemplo:

```
CRÍTICA · 76–100 · antes de qualquer coisa
 rank   id        title                                     type    agent
━━━━━  ━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━  ━━━━━━━━━━━
  98   BL-0007   Corrigir timeout do extrair_audiograma    bug     medicina
─────  ────────  ─────────────────────────────────────────  ──────  ───────────
  88   BL-0012   Validar schema antes de persistir          bug     ingestao

ALTA · 51–75 · pare assim que puder
 rank   id        title                                     type    agent
━━━━━  ━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━  ━━━━━━━━━━━
  72   BL-0009   Extrair cliente HTTP para módulo próprio   debt    core
```

### promote — virou trabalho real

Quando o item entra em execução (ex: virou spec/bugfix formal):

1. `status = "promovido"`; `updated` = hoje; `rank = null` (saiu da fila de ataque).
2. `promoted_to` = link do destino (ex: `specs/NNN-...` via `/speckit-specify`,
   ou o id do bugfix via `/speckit-bugfix-report`, se o projeto usa speckit).
3. Não apagar o item — o histórico de captura→promoção é útil.

> `em-andamento` é o estado intermediário (já começou, sem spec formal ainda — ex:
> worktree criada). `promovido` exige `promoted_to` preenchido.

### resolve / discard — encerrar

- `resolve`: trabalho feito (geralmente após a spec/bugfix promovido mergear).
  `status = "resolvido"`, `updated` = hoje, `rank = null`, `notes` ganha o link do
  PR/commit.
- `discard`: decidiu-se não fazer. `status = "descartado"`, `updated` = hoje,
  `rank = null`, `notes` registra o porquê. Não apagar.

Itens `resolvido`/`descartado` permanecem no JSON (auditoria); o `list` os esconde
por padrão.

## Regras inegociáveis

- **JSON é fonte única.** Nunca registrar item/status no `BACKLOG.md` nem espalhar
  TODOs equivalentes pelo código — duplicação gera drift.
- **Nunca reusar `id`** nem decrementar `next_id`.
- **`rank` é único e só vem do `format`.** Nenhuma outra operação inventa rank;
  números nunca se repetem; só itens `aberto`/`em-andamento` têm rank (o resto é
  `null`). Na saturação de uma faixa, `format` PARA (não repete número).
- **Validar enums** contra a chave `enums` do JSON antes de gravar.
- **Atualizar `updated`** (do item E do topo) a cada gravação; manter o JSON válido
  e parseável (rodar `python -m json.tool` ou equivalente se em dúvida).
- **Backlog ≠ spec.** Não é o lugar de especificar; é captura leve. Detalhe que
  cresce demais vira spec promovida, não um item gigante.
- **Bootstrap é idempotente.** Se `.specify/backlog.json` já existe, NUNCA
  sobrescrever no `init` — apenas complementar o que falta (`BACKLOG.md` ausente,
  seção ausente no `AGENTS.md` ou `CLAUDE.md` herdado).

## Exemplo de item

```json
{
  "id": "BL-0007",
  "type": "bug",
  "title": "Corrigir timeout do extrair_audiograma em PDFs > 20 páginas",
  "status": "aberto",
  "priority": "alta",
  "rank": 72,
  "agent": "medicina",
  "created": "2026-06-12",
  "updated": "2026-06-12",
  "source": "relato de UAT — PDF da clínica X estoura 60s",
  "detail": null,
  "related": ["app/medicina/extracao.py", "app/medicina/config.yaml"],
  "promoted_to": null,
  "notes": "Provável reasoning budget mal calibrado. Investigar antes de virar spec."
}
```
