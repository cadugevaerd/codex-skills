---
name: backlog-format
description: Propõe e aplica formatos de backlog com confirmação humana explícita.
argument-hint: "--db PATH --code ABC --format-code descriptive-code"
user-invocable: true
disable-model-invocation: true
---
# Format proposal/apply

`backlogctl` compatível com o contrato 2.0 deve estar instalado. Execute primeiro:

```sh
backlogctl --json doctor --db PATH
```

Em integrações de agente, `--json` deve vir antes da família de comandos.

## Propose

Para gerar uma proposta sem alterar itens:

```sh
backlogctl --json format propose --db PATH --code ABC --format-code descriptive-code --expires-at YYYY-MM-DD --context-id CTX-N [repeat] --change ABC-0001:high:1 [repeat]
```

Mostre ao usuário o diff estruturado da proposta e aguarde confirmação humana explícita. `propose` não altera itens nem aplica a proposta. Não há confirmação oculta ou implícita.

## Apply

Só aplique após confirmação humana explícita, usando o identificador da proposta:

```sh
backlogctl --json format apply --db PATH --id FMT-N --confirm
```

Não tente novamente erros de proposta obsoleta, expirada ou de confirmação. Explique o status retornado e, quando solicitado, gere uma nova proposta.

Use exclusivamente `backlogctl`; nunca manipule SQLite diretamente.

## Consulta

Use `format list` para listar formatos e `format show` para exibir um formato específico. Execute o doctor antes dessas operações também e preserve a saída estruturada quando `--json` for usado.
