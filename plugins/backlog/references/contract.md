# Backlog v2 — contrato documental canônico

## Matrix CLI, transporte e exit codes

`backlogctl` é a única fonte de verdade; skills não leem/escrevem SQLite ou JSON de estado. A forma global correta é `backlogctl [--json] <família> <comando> ...`; `--json` vem antes da família. `--db PATH` é uma flag de cada comando (não uma flag global).

Operações implementadas: `store init`, `doctor`; `backlog create|list|show|edit|archive|bind`; `item add|list|show|edit|transition|move|reconcile-status|archive`; `context add|list|show|supersede|revoke|expire`; `format list|show|propose|apply`; `export json|markdown|consolidated`.

- sucesso com `--json`: stdout contém exatamente um envelope com `{result:"ok",operation,contract_version:"2",changed,data,warnings,next_action}`;
- erro de domínio/not-found/validação: diagnóstico humano em stderr, exit 1; não tratar como envelope JSON de sucesso;
- uso inválido, comando desconhecido ou gramática inválida: usage em stderr, exit 2;
- doctor é diagnóstico seguro e não muta. Falha de doctor encerra a operação.

Não invente flags, subcomandos ou capabilities. Após um erro, reporte stderr e exit code; nunca fabrique sucesso nem faça fallback para arquivos legados.

Flags são command-scoped: uma flag válida em outra subcommand, ou apenas listada globalmente, continua inválida aqui e deve produzir exit 2. `item add --status STATE` define o snapshot inicial (omitido = `open`) e aceita os cinco status canônicos, inclusive `merged`; não é transição. `item transition` usa obrigatoriamente `--status`, nunca `--to`, e mantém a FSM normal; `merged` permanece terminal.

`item reconcile-status --id ID --status STATE --reason TEXT --confirm` é recuperação administrativa auditada: exige confirmação humana, razão não vazia e pode bypassar deliberadamente o grafo somente para reparo verificado. Não é fluxo de migração normal. `item archive --id ID --reason TEXT --confirm` é soft archive auditável para item sem fonte/teste/obsoleto; nunca apague nem acesse SQLite. List/export omitem arquivados por padrão; `show` e `list --all` os preservam para auditoria.

## Perfis, categories e entidades

Backlogs têm `code`, `name`, `profile`, `archived` e opcional `bound_path`. O item tem ID estável, `backlog_code`, `title` como resumo, `description` como descrição executável completa, category, status, criticality e position. Status canônicos: `open`, `in_progress`, `done`, `cancelled`, `merged`; `blocked` é condição, não status. Criticality: `critical`, `high`, `medium`, `low`.

`item add --description TEXT` grava a descrição completa. Em `item edit`, `--description TEXT` substitui, a flag omitida preserva e `--description ""` limpa explicitamente. JSON de `item show`, `item list` e `export json`/formatos JSON sempre inclui `description`, inclusive como string vazia.

## Ordem, posição, IDs, arquivo e bind

A ordem canônica é criticality descendente (`critical`, `high`, `medium`, `low`) e, dentro dela, position. Não existe limite artificial de 100 itens/position. `item move` altera posição; não renumere IDs. IDs são estáveis e não reutilizados. `backlog bind --code CODE --path PATH` associa o arquivo/caminho ao backlog; o bind pertence ao backlog e é preservado nos exports.

## Formatos

`export json` e `export markdown` são derivados e não mutam a fonte. O `export consolidated` canônico é `data={backlogs:[{code,name,profile,archived,bound_path,items:[...]}]}`; cada item fica dentro do backlog pai e não existe `data.items` no nível superior. JSON sempre expõe `description`; Markdown deve preservar a associação backlog/item e os códigos/status/criticality canônicos.

`format propose` cria uma proposta de alteração; mostre o diff estruturado e aguarde confirmação humana explícita. `format apply` só pode ser executado após essa confirmação, com `--confirm`; não há confirmação oculta. Propostas obsoletas ou expiradas exigem nova proposta.

## Contextos

A família `context` é implementada: `add|list|show|supersede|revoke|expire`. Toda mutação de contexto exige confirmação explícita do usuário e deve usar `backlogctl --json context ... --db PATH`. Nunca acesse SQLite diretamente.

## Compatibilidade e capabilities pendentes

Use o `backlogctl` fornecido pelo bootstrap, validado com SHA-256. Use o caminho exato emitido pelo hook ou pelo verificador manual; nunca presuma que está no PATH. Execute `backlogctl --version` e `backlogctl --json doctor` por esse caminho.

`merge`, `import` e `update` continuam não implementados como comandos CLI (ou disponíveis apenas como diagnóstico do doctor, quando expostos). A skill `backlog-import` é um workflow agent-led separado: proposta sem mutação, descrições legadas completas e execução confirmada pelos comandos públicos; não o trate como capability nativa nem prometa atomicidade.
