---
name: "code-debug"
description: "Diagnóstico disciplinado e diagnose-only: reproduz falhas, coleta evidências, testa hipóteses e entrega relatório de causa raiz, sem executar correções."
argument-hint: "<comando de debug/reprodução e contexto opcional>"
---

# Code Debug — diagnóstico de causa raiz, sem correção

Use esta skill quando receber um comando, stack trace, log, falha de teste/build ou descrição de bug e o objetivo for descobrir a causa raiz real.

O contrato padrão é **diagnose-only**:

```text
reproduzir → coletar evidências → testar hipóteses → concluir → relatório → STOP
```

## Contrato não negociável

- Nunca afirme a causa sem evidência direta.
- Nunca substitua investigação por palpite plausível.
- Hipóteses são permitidas apenas como itens testáveis; elas não são conclusão.
- Se a causa raiz não puder ser comprovada, declare `causa raiz não comprovada ainda` e registre a evidência que falta.
- Quando a causa raiz estiver comprovada, encerre a investigação após restaurar apenas a instrumentação temporária criada por esta execução e emitir o relatório.
- Não editar código, configuração, testes ou documentação como correção; não aplicar patch de produto; não validar fix; não criar commit, PR ou backlog; não investigar melhorias ou causas secundárias; não sugerir comandos de correção.
- Se o usuário pedir “debugue e corrija” na mesma invocação, execute somente o diagnóstico. Correção exige nova solicitação ou outro workflow.
- Não criar opção `--diagnose`: diagnóstico puro já é o comportamento padrão.

## Entrada esperada

O usuário deve passar pelo menos um destes:

```text
/code-debug <comando que reproduz o erro>
/code-debug <stack trace/log> + <comando esperado>
/code-debug <descrição do bug> + <como simular>
```

Se faltar o comando de reprodução, tente inferi-lo pelo projeto — README, scripts, Makefile, pyproject, testes, compose ou CI. Pergunte apenas quando não houver caminho recuperável.

## Fluxo obrigatório de investigação

1. **Registrar escopo e baseline**
   - Registre comando, diretório, branch/commit, ambiente e comportamento esperado.
   - Capture o estado inicial dos arquivos relevantes e a sujeira preexistente. Nunca apague ou reverta alterações que já existiam.

2. **Reproduzir o erro**
   - Rode exatamente o comando fornecido, quando seguro.
   - Capture `stdout`, `stderr`, exit code e logs relevantes.
   - Se a reprodução falhar por ambiente ausente, registre o bloqueio comprovado e tente uma reprodução menor.

3. **Coletar evidências antes de concluir**
   - Leia stack trace, chamadas imediatas, configurações, manifests, testes e logs relacionados.
   - Inspecione o estado real relevante: processos, portas, filesystem, banco, serviços, containers, rede ou permissões.
   - Quando útil, compare mudanças recentes nos arquivos suspeitos.

4. **Formar hipóteses testáveis**
   - Para cada hipótese, declare previsão, teste objetivo e condição de falsificação.
   - Teste uma variável significativa por vez.
   - Registre hipóteses eliminadas e a evidência que as refutou.
   - Não declare causa enquanto existirem explicações concorrentes plausíveis não testadas.

5. **Instrumentar somente quando necessário**
   - Prefira probes, logs temporários ou reprodução isolada que não alterem o produto.
   - Se uma edição temporária for indispensável, faça-a mínima e reversível e registre o delta criado.
   - Antes do relatório, remova exclusivamente a instrumentação criada por esta execução e confirme que o delta diagnóstico voltou a zero, preservando a sujeira preexistente.

6. **Comprovar ou limitar a conclusão**
   - Mostre a cadeia causal completa: condição inicial → código/configuração/estado → falha observada.
   - A causa raiz deve explicar os sintomas principais e ser confirmada por reprodução, teste, log, simulação ou experimento objetivo.
   - Um contrafactual pode ser executado em ambiente isolado para confirmar causalidade, mas não deve virar correção persistente.
   - Se faltar evidência, classifique como inconclusivo ou bloqueado, sem promover hipótese a fato.

7. **Emitir relatório e parar**
   - Use o formato obrigatório abaixo.
   - Após o marcador final, não execute nenhuma ação adicional nesta invocação.

## Evidência mínima para afirmar causa raiz

Uma conclusão só pode ser classificada como causa raiz quando houver:

- erro reproduzido ou log/trace confiável com origem clara;
- local exato do código, configuração ou estado que dispara a falha;
- explicação causal ligando esse local ao sintoma;
- verificação objetiva que confirme a causalidade;
- alternativas plausíveis eliminadas ou explicitamente limitadas.

Sem isso, use `Hipótese mais provável` e mantenha o status como `causa raiz não comprovada ainda`.

## Formato obrigatório da saída

````markdown
# Relatório de debug

## Status
- causa raiz comprovada | causa raiz não comprovada ainda | bloqueado por ambiente

## Sintoma reproduzido
- Comando/cenário: `<comando>`
- Resultado observado: <erro, exit code ou comportamento>

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| <log, teste ou leitura> | <arquivo ou comando> | <conclusão objetiva> |

## Caminho de investigação/Hipóteses eliminadas
1. <ação executada> → <resultado real>

## Causa raiz
<Preencher como causa somente se estiver comprovada. Caso contrário, escrever `causa raiz não comprovada ainda`.>

## Cadeia causal
<condição inicial → código/configuração/estado → falha observada>

## Arquivos envolvidos
- `<arquivo>`: <papel na falha>

## Limitações/incertezas
- <evidência ainda ausente ou `nenhuma para o sintoma reproduzido`>

Diagnóstico encerrado. Nenhuma correção foi executada.
````

## Regras de comunicação

- Seja direto e cite comandos, arquivos e linhas quando possível.
- Diferencie claramente fato, hipótese, experimento e conclusão.
- Não use linguagem de certeza sem evidência suficiente.
- Não invente saída de comandos, logs, arquivos ou APIs.
- O marcador final exato é: `Diagnóstico encerrado. Nenhuma correção foi executada.`
