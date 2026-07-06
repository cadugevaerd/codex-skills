---
name: "code-debug"
description: "Debug disciplinado por causa raiz: reproduz o erro a partir de um comando, coleta logs/evidencias, instrumenta quando necessario, evita suposicoes e entrega relatorio com causa raiz comprovada e sugestao de fix. Use quando o usuario passar um comando de debug, erro, stack trace, falha de teste, build ou comportamento inesperado."
argument-hint: "<comando de debug/reproducao e contexto opcional>"
---

# Code Debug — root-cause debugging sem chute

Use esta skill quando receber um comando, stack trace, log, falha de teste/build ou descricao de bug e o objetivo for encontrar a causa raiz real.

## Contrato nao negociavel

- Nunca afirme a causa sem evidencia direta.
- Nunca substitua investigacao por palpite plausivel.
- Hipoteses sao permitidas apenas como itens a testar; elas nao sao conclusao.
- Se a causa raiz nao puder ser comprovada com as evidencias disponiveis, diga explicitamente: `causa raiz nao comprovada ainda` e liste a proxima evidencia necessaria.
- Prefira corrigir a causa raiz, nao sintomas.
- Ao adicionar logs/instrumentacao, faca mudancas minimas, reversiveis e explique exatamente onde foram adicionadas.

## Entrada esperada

O usuario deve passar pelo menos um destes:

```text
/code-debug <comando que reproduz o erro>
/code-debug <stack trace/log> + <comando esperado>
/code-debug <descricao do bug> + <como simular>
```

Se faltar o comando de reproducao, tente inferir pelo projeto (README, package scripts, Makefile, pyproject, tests, compose, CI). Pergunte apenas quando nao houver caminho recuperavel.

## Fluxo obrigatorio de investigacao

1. **Registrar o escopo**
   - Anote comando recebido, diretorio, branch/commit, ambiente e comportamento esperado.
   - Crie uma lista curta de TODOs antes de executar investigacoes longas.

2. **Reproduzir o erro**
   - Rode exatamente o comando fornecido, quando seguro.
   - Capture `stdout`, `stderr`, exit code e trechos relevantes de log.
   - Se falhar por dependencia/ambiente ausente, registre isso como bloqueio comprovado e tente uma reproducao menor.

3. **Coletar evidencias antes de concluir**
   - Leia arquivos diretamente relacionados ao erro: stack trace, chamadas imediatas, configs, manifests, testes, CI, variaveis e logs.
   - Inspecione estado real quando relevante: processos, portas, filesystem, banco, servicos, container, rede ou permissoes.
   - Se houver historico Git util, compare mudancas recentes nos arquivos suspeitos.

4. **Formar hipoteses testaveis**
   - Para cada hipotese, defina uma prova objetiva: comando, log esperado, breakpoint/log temporario, teste minimo ou leitura de estado.
   - Descarte hipoteses que nao resistirem aos dados.
   - Nao declare causa enquanto houver explicacoes concorrentes plausiveis nao testadas.

5. **Instrumentar quando necessario**
   - Adicione logs temporarios apenas nos pontos de decisao relevantes.
   - Use mensagens com valores concretos: inputs, IDs, paths, flags, tipo, contagem, status, excecao original.
   - Rode novamente a reproducao e use os novos logs para estreitar a cadeia causal.
   - Remova logs temporarios ou marque claramente se devem virar observabilidade permanente.

6. **Comprovar a causa raiz**
   - Mostre a cadeia causal completa: condicao inicial -> codigo/config -> falha observada.
   - A causa raiz precisa explicar todos os sintomas principais e ser confirmada por pelo menos uma reproducao/prova.
   - Quando possivel, valide tambem o contrafactual: ao alterar a condicao suspeita ou aplicar patch minimo, o erro desaparece.

7. **Sugerir fix**
   - Proponha o menor fix seguro que ataque a causa raiz.
   - Inclua riscos, efeitos colaterais e testes de regressao recomendados.
   - Se aplicar o fix estiver no escopo, faca a alteracao e rode a verificacao original.

## Evidencia minima para afirmar causa raiz

Uma conclusao so pode ser escrita como causa raiz quando houver:

- erro reproduzido ou log/trace confiavel com origem clara;
- local exato do codigo/config/estado que dispara a falha;
- explicacao causal que conecte o local ao sintoma;
- verificacao objetiva: teste, comando, log, simulacao ou experimento que confirme a causalidade.

Sem isso, use `Hipotese mais provavel`, nao `Causa raiz`.

## Formato obrigatorio da saida

````markdown
# Relatorio de debug

## Resumo
- Status: causa raiz comprovada | causa raiz nao comprovada ainda | bloqueado por ambiente
- Comando/reproducao: `<comando>`
- Sintoma observado: <erro/exit code/comportamento>

## Evidencias coletadas
| Evidencia | Fonte | O que comprova |
|---|---|---|
| <log/teste/leitura> | <arquivo/comando> | <conclusao objetiva> |

## Caminho de investigacao
1. <acao executada> -> <resultado real>
2. <acao executada> -> <resultado real>

## Causa raiz
<Somente preencher como causa se estiver comprovada. Explicar a cadeia causal.>

## Sugestao de fix
- Mudanca recomendada: <fix>
- Por que resolve a causa raiz: <explicacao>
- Riscos/efeitos colaterais: <lista>

## Verificacao recomendada
```bash
<comandos para validar o fix>
```

## Pendencias / incertezas
- <somente se ainda faltar evidencia>
````

## Regras de comunicacao

- Seja direto e cite comandos/arquivos/linhas quando possivel.
- Diferencie claramente `fato`, `hipotese`, `experimento` e `conclusao`.
- Nao use linguagem de certeza (`e`, `com certeza`, `causa raiz`) sem evidencia suficiente.
- Nao invente saida de comandos, logs, arquivos ou APIs. Se nao rodou/leu, diga que nao rodou/leu.
