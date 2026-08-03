# Backlog v2 — contrato canônico

## Versões

`backlogctl` é a única fonte de verdade. CLI **2.3.0**, DB **schema 5**, envelope geral `contract_version:"2"` e documento do import `contract_version:"3"`. Skills nunca leem/escrevem SQLite diretamente.

Formas globais: `backlogctl [--json] doctor --db PATH` para o comando de topo, ou `backlogctl [--json] <família> <comando> ...` para famílias; `--json` vem antes do comando/família. Sucesso: `{result:"ok",operation,contract_version:"2",changed,data,warnings,next_action}`. Erros de domínio: exit 1 e diagnóstico em stderr; gramática inválida: exit 2.

## Superfície

- `store init`, `doctor`
- `backlog create|list|show|edit|archive|bind`
- `item add|list|show|edit|transition|move|reconcile-status|archive`
- `context add|list|show|supersede|revoke|expire`
- `decision record|list`
- `format list|show|propose|apply|expire`
- `export json|markdown|consolidated`
- `merge preview|list|show|apply|expire`
- `import preview|apply`
- `todo scan|apply`
- `update check|install|migrate`

## Segurança transacional

Consultas, `merge preview|list|show`, `import preview`, `todo scan` e `update check` não alteram domínio. Toda mutação, inclusive administrativa e `apply`, exige confirmação humana explícita conforme a rota.

`item add --status STATE` define o snapshot inicial validado; omitido = `open`. `item edit` preserva description omitida. `item reconcile-status --reason ... --confirm` é reparo excepcional auditado, não transição comum. `item archive --reason ... --confirm` é arquivo lógico, nunca DELETE.

`merge preview --source SRC --target DST` persiste `MRG-N` e snapshots sem alterar itens; `merge apply --id MRG-N --confirm` revalida estado, expiração e revisions. Não existe hash de merge.

`import preview --file FILE` valida JSON v3 e calcula SHA sem mutar; `import apply --expected-sha256 SHA --confirm` exige os mesmos bytes e aplica atomicamente. JSON v1 usa `references/migration-v1-to-v2.md`.

`todo scan --code ABC --path SOURCE` é puro, explícito e somente profile `software`; `todo apply` exige os mesmos argumentos, SHA e `--confirm`, sem alterar fontes.

`backlogctl version` imprime exatamente a versão semântica, por exemplo `2.3.0`, sem prefixo, sufixo ou texto adicional. `update install` verifica SHA e essa saída exata de `version` antes/depois do rename com rollback. `update migrate` exige DB existente, integrity check e backup antes das migrations; schema futuro é bloqueado.
