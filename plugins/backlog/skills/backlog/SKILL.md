---
name: "backlog"
description: "Registrar, triar e promover itens diferidos (features, bugs, débitos técnicos, chores) na fonte da verdade GLOBAL ~/.backlog/backlog.json — um backlog único para TODOS os repositórios, com o repositório-alvo (campo `repo`) persistido em cada item. Use quando identificar trabalho que não será feito agora, quando for revisar/promover/resolver o backlog de qualquer repo, quando houver TODOs/FIXMEs soltos, ou quando a estrutura global ainda não existir (a skill faz bootstrap)."
argument-hint: "add | list | format | promote | resolve | discard | init <texto livre do que fazer> [repo=<nome>]"
metadata:
  author: "civilmaster"
  source: "originada no projeto masterai-agents-backend; promovida a skill global; migrada para backlog global único (~/.backlog/backlog.json)"
user-invocable: true
disable-model-invocation: false
---

# Skill: backlog

Opera a **fonte da verdade GLOBAL dos itens diferidos** — um backlog **único**
em `~/.backlog/backlog.json` que vale para **todos os repositórios**. Cada item
carrega o **repositório-alvo** (campo `repo`), então você registra/triagem/consulta
de qualquer pasta e sabe **qual problema resolver, em qual repo**, independente de
onde a sessão está rodando.

> **Mudança de modelo (v2).** Antes o backlog era por-projeto
> (`.specify/backlog.json` na raiz de cada repo). Agora é **global único**: a skill
> sempre lê/grava `~/.backlog/backlog.json`, ignorando o CWD para fins de
> armazenamento. O CWD serve **só** para detectar o `repo` do item no `add`.

## Fonte da verdade

`~/.backlog/backlog.json` (expandir `~` para o home do usuário) é o **único**
registro canônico, para todos os repos. Estrutura:

```jsonc
{
  "version": 2,
  "updated": "YYYY-MM-DD",       // data da última edição do arquivo
  "next_id": { "<repo>": <int> },// próximo número livre p/ BL-NNNN, POR REPO
  "enums": { "type": [...], "status": [...], "priority": [...] },
  "items": [ { /* item */ } ]
}
```

Cada item:

| campo | tipo | regra |
|---|---|---|
| `id` | string | `BL-NNNN` (zero-padded, 4 dígitos). **Único dentro do seu `repo`**; nunca reusar dentro do repo. |
| `repo` | string | **repositório-alvo** onde o trabalho será feito (nome do repo, ex: `masterai-agents-backend`). Obrigatório. Identidade do item = `(repo, id)`. |
| `repo_path` | string\|null | caminho absoluto do repo no disco (ex: `/home/.../projetos/<repo>`), p/ navegação. `null` se desconhecido. |
| `type` | enum | `feature` \| `bug` \| `debt` \| `chore`. |
| `title` | string | uma linha, no infinitivo quando for ação. |
| `status` | enum | `aberto` \| `em-andamento` \| `promovido` \| `resolvido` \| `descartado`. |
| `priority` | enum | `critica` \| `alta` \| `media` \| `baixa`. Severidade — ver "Severidade & rank". |
| `rank` | int\|null | 1–100, **único dentro do mesmo `repo`**, maior = mais importante. Atribuído **só** pela operação `format` (re-rank), por repo. `null` fora do universo do rank (status ≠ `aberto`/`em-andamento`). |
| `agent` | string\|null | módulo/runtime/área afetada, ou `null` se transversal/infra. |
| `created` | date | data de captura (não muda). |
| `updated` | date | última mudança no item. |
| `due` | date\|null | **data alvo de entrega** (ISO `YYYY-MM-DD`), **opcional**. `null` quando não há prazo. Eixo de urgência: no `format`, itens com `due` sobem **dentro da sua faixa de severidade** e uma `due` próxima/vencida pode justificar subir a severidade. Ausência do campo = `null` (sem migração). |
| `source` | string | de onde nasceu (grilling, bug em prod, e-mail, varredura…). |
| `detail` | string\|null | path de `<repo_path>/docs/backlog/<id>-*.md` quando há detalhe longo; senão `null`. |
| `related` | string[] | paths de código, specs, ADRs, princípios (relativos ao `repo`). |
| `promoted_to` | string\|null | link da spec/bugfix quando `status=promovido`. |
| `notes` | string | contexto curto: o que fazer, esforço, restrições. |

> **Identidade = `(repo, id)`.** O `BL-NNNN` é único só dentro do seu repo — dois
> repos podem ter `BL-0001` (itens diferentes), desambiguados pelo `repo`. Por isso
> `next_id` é um **mapa por repo**, e o `rank` também é **único por repo**.

## Bootstrap — quando a estrutura global não existe

**Antes de qualquer operação**, garanta que `~/.backlog/backlog.json` existe. Se
**não** existir (1ª vez na máquina, ou via comando explícito `init`), crie o
skeleton abaixo (substituir `<hoje>` pela data atual) e informe. **Nunca**
sobrescreva um arquivo existente — se já existe, só siga com a operação pedida.

```json
{
  "_about": "Backlog GLOBAL único de itens diferidos (features, bugs, débitos, chores) de TODOS os repositórios. Cada item carrega `repo` (repositório-alvo) e `repo_path`. Identidade = (repo, id): o BL-NNNN é único DENTRO do seu repo. Fonte da verdade única: ~/.backlog/backlog.json. Operado pela skill global /backlog (Claude Code e Codex).",
  "version": 2,
  "updated": "<hoje>",
  "next_id": {},
  "enums": {
    "type": ["feature", "bug", "debt", "chore"],
    "status": ["aberto", "em-andamento", "promovido", "resolvido", "descartado"],
    "priority": ["critica", "alta", "media", "baixa"]
  },
  "items": []
}
```

> A skill **não** cria mais `.specify/backlog.json`, `BACKLOG.md` nem seção no
> `CLAUDE.md`/`AGENTS.md` do projeto — o armazenamento é global. Backlogs
> por-projeto pré-existentes são **legado migrado**; ignore-os (a fonte da verdade
> é só `~/.backlog/backlog.json`).

> **Upgrade aditivo do enum `priority` (idempotente).** Em **toda** execução, se o
> `enums.priority` não contém `"critica"`, adicione-o no topo
> (`["critica","alta","media","baixa"]`). Aditivo e não-destrutivo — não
> reclassifica nenhum item. Não pergunte, faça e informe.

## Detecção do `repo` (no `add` e na varredura)

O `repo` do item é o **repositório-alvo** onde o trabalho será feito:

1. Se o texto livre traz `repo=<nome>` (ou "no repo X / no projeto X"), use-o.
2. Senão, detecte pelo CWD: `git rev-parse --show-toplevel` → basename é o `repo`,
   e o toplevel é o `repo_path`.
3. Se o CWD não é um repo git e nenhum `repo` foi dado, **pergunte** qual repo —
   não invente nem grave sem `repo`.

> Para registrar item de **outro** repo (não o CWD), basta `repo=<nome>` no texto.
> Se o repo já aparece em outros itens, reuse o mesmo `repo_path`.

## Varredura — backlog não estruturado (toda execução)

Em **toda** invocação, após o bootstrap e ANTES da operação pedida, varra o
**repo do CWD** (não os outros) por trabalho diferido fora da fonte da verdade:

1. **Código:** grep por `TODO`, `FIXME`, `XXX`, `HACK` — excluindo
   dependências/artefatos (`.git`, `node_modules`, `.venv`, `venv`, `vendor`,
   `dist`, `build`, `__pycache__`, `.claude/worktrees`, locks) e marcadores que já
   referenciam um id (`BL-NNNN`).
2. **Notas:** `TODO.md`, `NOTES.md`, `PENDENCIAS.md` e seções
   "Backlog"/"Pendências"/"TODO" em markdowns. Inclui `.specify/backlog.json`
   legado **não migrado**: se achar itens lá que não existem no global, ofereça
   migrá-los (stamp `repo` = repo do CWD).
3. **Classificar cada achado:**
   - **Trabalho diferido real** → **migrar**: criar item `BL-NNNN` (no `next_id` do
     repo do CWD) com `repo` = repo do CWD, `source` =
     `"varredura /backlog — <path>:<linha>"`; substituir o original por referência
     (`TODO(BL-NNNN): <resumo>` no código; ponteiro no markdown).
   - **Trivial/local** → deixar como está.
   - **Ambíguo** → não migrar em silêncio: listar como candidato (path:linha + por quê).
4. **Reportar ao final:** itens migrados (`BL-NNNN ← path:linha`) e candidatos
   ambíguos. Nada achado → não reporte nada.

**Idempotência:** `TODO(BL-NNNN)` não gera item novo; antes de criar, cheque
duplicata por `(repo, title)`/`related` contra os itens existentes (inclusive
`resolvido`/`descartado`). Dezenas de achados → migre só os claros e liste o resto.

## Severidade & rank

Dois eixos descrevem a urgência: a **severidade** (`priority`, qualitativo) e o
**rank** (`rank`, quantitativo, atribuído só pelo `format`, **por repo**).

**Severidade (`priority`) — 4 níveis:**

| nível | significado |
|---|---|
| `critica` | Precisa implementar **antes de qualquer coisa**. Bloqueia o resto. |
| `alta` | Pode-se fazer outras coisas, mas é recomendado **parar assim que puder** para implementar. |
| `media` | Não é obrigatório, mas **deixa o código melhor** quando feito. |
| `baixa` | Apenas **estético** / cosmético. |

**Data alvo (`due`) — eixo de urgência opcional.** Itens com prazo de entrega
carregam `due` (ISO `YYYY-MM-DD`); os demais têm `due = null`. A `due` **não cria
uma faixa nova** nem atropela a severidade: a criticidade continua sendo o eixo
primário (uma `critica` sem prazo ainda fica acima de uma `media` com prazo). A
`due` atua **dentro da faixa** (no `format`, itens com `due` sobem na faixa, `due`
mais próxima primeiro) e como **sinal de re-triagem** (prazo apertado/vencido pode
justificar subir a severidade — ex.: `media`→`alta`).

**Rank (`rank`) — score 1–100 com faixas por severidade, único POR REPO.** Maior =
mais importante; responde "dentro de uma mesma severidade, qual atacar primeiro" e
dá a **ordem de ataque única dentro daquele repo**. Faixas:

| severidade | faixa | slots |
|---|---|---|
| `critica` | 76–100 | 25 |
| `alta` | 51–75 | 25 |
| `media` | 26–50 | 25 |
| `baixa` | 1–25 | 25 |

O rank **só** é (re)calculado pelo `format`, escopado a um repo. Fora dele
(`add`/`promote`/`resolve`/`discard`) o rank nasce `null` e só é preenchido/limpo
pelas regras de cada operação.

## Operações

Determine a operação pelo argumento (`add`/`list`/`format`/`promote`/`resolve`/
`discard`/`init`) ou pelo texto livre. Sempre **leia o JSON global antes de editar**
e **reescreva o arquivo inteiro válido** (JSON puro, sem comentários).

### add — registrar item novo

1. Ler `~/.backlog/backlog.json`.
2. Determinar `repo`/`repo_path` (ver "Detecção do `repo`").
3. `n = next_id.get(repo, 1)`; `id = "BL-" + zero_pad(n, 4)`.
4. Preencher os campos. Mínimos obrigatórios: `id`, `repo`, `type`, `title`,
   `status` (`aberto`), `priority`, `created` (hoje), `updated` (hoje), `source`.
   Tente preencher `repo_path`, `agent`, `related`, `notes`. `rank` nasce `null`.
   Se o texto livre traz uma data de entrega/prazo (`due=<data>`, "entregar até",
   "prazo", "deadline"), normalize para ISO `YYYY-MM-DD` e grave em `due`; senão
   `due = null`.
5. Se há detalhe longo, criar `<repo_path>/docs/backlog/<id>-<slug>.md` (header
   apontando id + `~/.backlog/backlog.json`) e setar `detail` para esse path.
6. `next_id[repo] = n + 1`; `updated` (topo) = hoje; `items.push(item)`.
7. Confirmar ao usuário: `repo` + id atribuído + resumo.

> Antes de criar, **cheque duplicatas** por `(repo, title)`/`related` — se já existe
> item equivalente **no mesmo repo**, atualize-o em vez de duplicar.

### list — triar (read-only)

`list` é **read-only**: lê o JSON e exibe, **nunca muta** nem calcula rank.
Apresenta tabela com coluna **`repo`** (repo · id · type · title · status · priority
· rank · due · agent). Suporta filtros do texto livre: `repo=<nome>` (ou "do repo X"),
`status` (default: esconder `resolvido`/`descartado`), `agent`, `type`, `priority`.
**Default sem filtro de repo = mostra TODOS os repos**, agrupados por `repo`. Dentro
de cada repo, ordenar por priority (`critica`→`alta`→`media`→`baixa`), depois `rank`
desc (sem rank por último; entre os sem rank, quem tem `due` antes, `due` mais
próxima primeiro), depois id.

### format — reorganizar (re-triar severidade + atribuir rank) — POR REPO

`format` reorganiza o backlog de **um repo** (a ordem de ataque é por repo): re-avalia
a severidade e atribui o `rank` 1–100 dentro daquele repo. **Muta** o JSON, só **após
confirmação**.

**Escopo:** um repo por vez. Determine o repo: `repo=<nome>` no texto, senão o repo
do CWD, senão pergunte. (`repo=all` → roda repo-a-repo, confirmando cada um.)

**Universo:** itens **daquele repo** com `status` ∈ {`aberto`, `em-andamento`}.
Itens `promovido`/`resolvido`/`descartado` ficam fora; seu `rank` é forçado a `null`.

Passos:

1. **Ler** o JSON e aplicar o upgrade aditivo do enum `priority`.
2. **Coletar** os itens ativos **do repo escopado**.
3. **Re-triar a severidade** de cada um conforme as definições (crítica/alta/media/
   baixa), usando julgamento a partir de `type`, `notes`, `related`, `source` e
   `due`. Pode mudar o `priority`. Uma `due` próxima ou já vencida é **sinal forte
   de urgência** — considere subir a severidade (ex.: `media`→`alta`) quando o prazo
   aperta.
4. **Ordenar dentro de cada faixa** (a criticidade da faixa é preservada — só
   reordena internamente):
   - **Itens com `due` vêm antes dos sem `due`**, sempre dentro da mesma faixa.
   - Entre os **com `due`**: `due` mais próxima primeiro (vencida = mais urgente);
     empate quebrado por impacto + bloqueio, depois menor esforço (quick win).
   - Entre os **sem `due`**: impacto + bloqueio primeiro (sobe quem destrava outros
     / maior impacto); empate quebrado por menor esforço (quick win).
5. **Atribuir o `rank`** mapeando cada faixa ao intervalo (crítica 76–100, alta
   51–75, média 26–50, baixa 1–25): topo da faixa recebe o maior número disponível.
   Números **distintos dentro do repo**, nunca repetidos. Gaps permitidos sem sair
   da faixa.
6. **Saturação (fail-loud).** Se uma faixa tiver mais itens que slots (>25), **PARE**
   — não repita número nem invada faixa vizinha. Reporte a faixa saturada e peça
   re-triagem (rebaixar, resolver/descartar, ou quebrar itens).
7. **Gate de confirmação.** Apresente a proposta (view agrupada abaixo) destacando
   mudanças de severidade (`BL-0007 alta→critica`) e ranks. **Só grave após o OK.**
8. **Gravar.** Para cada item alterado: setar `priority` (se mudou) e `rank`,
   `updated` = hoje. Garantir `rank=null` fora do universo. Atualizar `updated` do
   topo. Reescrever o JSON inteiro válido.

**Saída — view agrupada (box-drawing).** Cabeçalho do repo, depois um bloco por
severidade (label + faixa + descrição) com tabela box-drawing (`━` no header, `─`
entre linhas), colunas `rank | id | title | due | type | agent`, ordenada por `rank`
desc. A coluna `due` mostra a data alvo (`—` quando `null`). Grupos vazios omitidos.
Exemplo:

```
repo: masterai-agents-backend

CRÍTICA · 76–100 · antes de qualquer coisa
 rank   id        title                                     due         type    agent
━━━━━  ━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━  ━━━━━━━━━━━
  98   BL-0007   Corrigir timeout do extrair_audiograma    2026-06-30  bug     medicina
─────  ────────  ─────────────────────────────────────────  ──────────  ──────  ───────────
  88   BL-0012   Validar schema antes de persistir          —           bug     ingestao

ALTA · 51–75 · pare assim que puder
 rank   id        title                                     due         type    agent
━━━━━  ━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━  ━━━━━━  ━━━━━━━━━━━
  72   BL-0009   Extrair cliente HTTP para módulo próprio   —           debt    core
```

### promote — virou trabalho real

1. `status = "promovido"`; `updated` = hoje; `rank = null` (saiu da fila).
2. `promoted_to` = link do destino (ex: `specs/NNN-...`, id do bugfix), no repo do item.
3. Não apagar o item — o histórico captura→promoção é útil.

> `em-andamento` é o intermediário (já começou, sem spec formal — ex: worktree).
> `promovido` exige `promoted_to` preenchido.

### resolve / discard — encerrar

- `resolve`: trabalho feito. `status = "resolvido"`, `updated` = hoje, `rank = null`,
  `notes` ganha o link do PR/commit.
- `discard`: decidiu-se não fazer. `status = "descartado"`, `updated` = hoje,
  `rank = null`, `notes` registra o porquê. Não apagar.

Itens `resolvido`/`descartado` permanecem no JSON (auditoria); o `list` os esconde
por padrão. Ao referenciar um item para encerrar, identifique-o por `(repo, id)`
quando o `BL-NNNN` puder existir em mais de um repo.

## Regras inegociáveis

- **`~/.backlog/backlog.json` é a fonte única e global.** Nunca registrar
  item/status em `.specify/backlog.json` de projeto, em `BACKLOG.md` nem espalhar
  TODOs equivalentes pelo código — duplicação gera drift.
- **Identidade = `(repo, id)`.** Todo item TEM `repo`. Nunca grave item sem `repo`.
  `BL-NNNN` é único dentro do repo; `next_id` é por repo (nunca decrementar nem
  reusar dentro do mesmo repo).
- **`rank` é único por repo e só vem do `format`.** Nenhuma outra operação inventa
  rank; números não se repetem dentro de um repo; só itens `aberto`/`em-andamento`
  têm rank. Na saturação de uma faixa, `format` PARA.
- **Validar enums** contra a chave `enums` antes de gravar.
- **Atualizar `updated`** (do item E do topo) a cada gravação; manter o JSON válido
  (rodar `python -m json.tool` se em dúvida).
- **Backlog ≠ spec.** Captura leve; detalhe que cresce vira spec promovida.
- **Bootstrap é idempotente.** Se `~/.backlog/backlog.json` já existe, NUNCA
  sobrescrever — só complementar o que falta (ex: enum `critica`).

## Exemplo de item

```json
{
  "id": "BL-0007",
  "repo": "masterai-agents-backend",
  "repo_path": "/home/caraujo/projetos/masterai-agents-backend",
  "type": "bug",
  "title": "Corrigir timeout do extrair_audiograma em PDFs > 20 páginas",
  "status": "aberto",
  "priority": "alta",
  "rank": 72,
  "agent": "medicina",
  "created": "2026-06-12",
  "updated": "2026-06-12",
  "due": "2026-06-30",
  "source": "relato de UAT — PDF da clínica X estoura 60s",
  "detail": null,
  "related": ["app/medicina/extracao.py", "app/medicina/config.yaml"],
  "promoted_to": null,
  "notes": "Provável reasoning budget mal calibrado. Investigar antes de virar spec."
}
```
