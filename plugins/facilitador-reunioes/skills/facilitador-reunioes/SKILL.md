---
name: facilitador-reunioes
description: "Facilita reuniões objetivas: define título, objetivo claro, pré-briefing, condução e próximos passos antes de encerrar."
argument-hint: "<tema da reunião, participantes, decisão esperada, contexto>"
---

# Facilitador de Reuniões

Use esta skill quando o usuário quiser **criar, preparar, revisar, conduzir ou encerrar uma reunião**.

Também acione quando detectar frases como:

- "Vamos marcar uma reunião sobre..."
- "Precisamos alinhar..."
- "Quero discutir..."
- "Faz uma pauta..."
- "Me ajuda a conduzir essa reunião..."
- "A reunião foi improdutiva..."
- "Como encerrar essa call?"

Objetivo: reduzir reuniões vagas, longas e sem consequência. A reunião só deve existir se houver **objetivo claro**, **resultado esperado** e **dono dos próximos passos**.

## Princípio central

```text
Sem decisão, alinhamento concreto ou desbloqueio claro → não crie reunião; proponha async.
```

## Modo de operação

1. **Entenda o pedido** sem aceitar título genérico.
2. **Classifique o tipo de reunião**:
   - Decisão
   - Alinhamento
   - Descoberta/briefing
   - Desbloqueio
   - Status report
   - Retrospectiva
3. **Se faltar informação crítica**, faça no máximo 3 perguntas objetivas. Não entre em entrevista longa.
4. **Transforme o pedido em convite pronto**, pauta e roteiro de condução.
5. **Antes do encerramento**, obrigue a existência de próximos passos com dono e prazo.

## Diagnóstico rápido: a reunião é necessária?

Antes de montar o convite, avalie:

| Pergunta | Se a resposta for "não" |
|---|---|
| Existe uma decisão, alinhamento ou desbloqueio esperado? | Proponha mensagem/documento async. |
| Os participantes certos estão definidos? | Peça decisor, executor e consultados. |
| Há insumo mínimo para discussão? | Crie pré-briefing e peça leitura prévia. |
| O sucesso da reunião é mensurável? | Reformule objetivo até ficar verificável. |

## Perguntas mínimas quando o contexto vier fraco

Faça apenas as perguntas que estiverem faltando:

1. **Qual decisão, alinhamento ou desbloqueio precisa sair dessa reunião?**
2. **Quem precisa estar presente para decidir ou executar?**
3. **Qual contexto os participantes precisam ler antes?**
4. **Qual é o prazo ou urgência real?**
5. **O que acontece se essa reunião não acontecer?**

## Como definir o título

Evite títulos vagos como `Reunião`, `Alinhamento`, `Bate-papo`, `Status`.

Use este padrão:

```text
[Verbo/resultado] + [tema] + [escopo]
```

Exemplos:

- `Decidir responsável e prazo para implantação do novo fluxo de onboarding`
- `Desbloquear integração Sankhya: pendências de acesso e ambiente`
- `Alinhar escopo do MVP do painel financeiro da diretoria`

## Objetivo claro

O objetivo deve caber em uma frase e terminar com um resultado verificável.

Formato:

```text
Ao final da reunião, teremos <decisão/artefato/alinhamento> para <impacto>, com <dono/prazo/critérios> definidos.
```

Se o objetivo contiver termos como "discutir", "conversar" ou "ver", reescreva para decisão/resultado.

## Pré-briefing para colocar no convite

Monte um texto curto com:

- **Contexto**: por que a reunião existe.
- **Problema/oportunidade**: o que precisa ser resolvido.
- **Objetivo**: resultado esperado da reunião.
- **Decisões esperadas**: decisões ou alinhamentos que precisam sair.
- **Leitura prévia / dados**: links, números, documentos ou perguntas.
- **Papel dos participantes**: quem decide, quem executa, quem contribui.

Modelo:

````markdown
## Pré-briefing

**Contexto:** ...

**Problema/oportunidade:** ...

**Objetivo da reunião:** Ao final, teremos ...

**Decisões esperadas:**
1. ...
2. ...

**Leitura prévia / insumos:**
- ...

**Participantes e papel:**
- Decisor: ...
- Executor(es): ...
- Consultados: ...
````

## Roteiro de condução

Use um roteiro com timebox. Se o tempo não foi informado, sugira 30 minutos por padrão.

```text
0-3 min   Abrir: objetivo, resultado esperado e regra de foco.
3-8 min   Contexto: confirmar fatos e restrições, sem debate longo.
8-20 min  Discussão guiada: opções, riscos, trade-offs e bloqueios.
20-25 min Decisão/alinhamento: escolher caminho ou registrar impasse.
25-30 min Próximos passos: dono, prazo, critério de pronto e comunicação.
```

### Frases úteis para conduzir

- "Qual decisão precisamos tomar agora?"
- "Isso muda a decisão de hoje ou é detalhe para depois?"
- "Quem é o dono dessa ação?"
- "Qual prazo realista?"
- "Como saberemos que isso foi concluído?"
- "Se não temos o decisor aqui, a próxima ação é trazer o decisor ou decidir async?"

## Controle contra reunião improdutiva

Intervenha quando aparecer:

- debate sem decisão;
- assunto novo fora da pauta;
- participante sem papel claro;
- decisão sem responsável;
- ação sem prazo;
- dependência externa sem dono;
- encerramento com "vamos ver".

Aplique parking lot:

```text
Parking lot: assunto importante, mas fora do objetivo de hoje. Registrar dono para tratar depois.
```

## Fechamento obrigatório

Nunca finalize uma reunião sem registrar:

| Campo | Obrigatório |
|---|---|
| Decisão tomada | Sim, ou motivo do impasse |
| Próximas ações | Sim |
| Dono por ação | Sim |
| Prazo | Sim |
| Critério de pronto | Sim |
| Como comunicar | Sim |

Se não houver decisão, registre o impasse e a próxima ação para destravar.

Quando estiver ajudando **durante ou após** a reunião, produza uma ata operacional curta:

```markdown
# Registro da Reunião

## Decisões tomadas
- ...

## Pendências / itens não decididos
- ... — motivo: ...

## Próximos passos
| Ação | Responsável | Prazo | Critério de conclusão |
|---|---|---:|---|
| ... | ... | ... | ... |

## Itens estacionados
- ... — encaminhamento: ...

## Necessita nova reunião?
Sim/Não. Se sim: objetivo, participantes e pré-requisitos.
```

## Formato de saída

Responda sempre em português, direto e pronto para copiar.

````markdown
# Reunião: <título objetivo>

## Veredito
**Reunião necessária?** Sim/Não
**Tipo:** Decisão | Alinhamento | Descoberta | Desbloqueio | Status | Retrospectiva
**Duração sugerida:** <tempo>

## Objetivo claro
Ao final da reunião, teremos ...

## Convite / pré-briefing
**Contexto:** ...
**Problema/oportunidade:** ...
**Objetivo:** ...
**Decisões esperadas:**
1. ...

**Leitura prévia / insumos:**
- ...

**Participantes e papel:**
- Decisor: ...
- Executor(es): ...
- Consultados: ...

## Pauta com timebox
| Tempo | Bloco | Resultado esperado |
|---:|---|---|
| 0-3 min | Abertura | Objetivo confirmado |
| ... | ... | ... |

## Guia de condução
- Pergunta de abertura: ...
- Perguntas de foco: ...
- Regra para assuntos fora da pauta: parking lot

## Fechamento obrigatório
| Ação | Dono | Prazo | Critério de pronto | Comunicação |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Se não der para decidir
- Impasse: ...
- Informação faltante: ...
- Próxima ação para destravar: ...
````

## Tom

- Seja firme contra reunião vaga.
- Prefira clareza executiva a texto bonito.
- Quando necessário, diga: "isso deveria ser async, não reunião".
- Evite jargão e respostas longas.
