# Prompt Engineering Foundations

Use este guia para transformar uma mudanca de prompt em um experimento reproduzivel. Ele cobre fundamentos de instrucao, contexto, exemplos, formato e amostragem; tecnicas avancadas como RAG, ReAct e fine-tuning ficam fora deste contrato.

## Estrutura do prompt

Um prompt pode combinar:

- **Instrucao**: tarefa especifica que o modelo deve executar;
- **Contexto**: informacao externa relevante para orientar a resposta;
- **Dados de entrada**: pergunta ou conteudo a processar;
- **Indicador de saida**: tipo e formato esperado da resposta.

Nem todo componente e obrigatorio. Comece com o menor prompt que expressa a tarefa e adicione componentes somente quando um failure observado justificar a mudanca.

Template base:

```text
### Instrucao ###
<Tarefa especifica>

Contexto:
<Informacao relevante>

Entrada:
<Dado ou pergunta>

Saida:
<Tipo ou formato esperado>
```

## Zero-shot e few-shot

Comece sem demonstracoes:

```text
<Instrucao>
```

Para pergunta e resposta:

```text
Q: <Pergunta>?
A:
```

Adicione demonstracoes quando o zero-shot nao obedecer ao comportamento ou formato:

```text
Q: <Pergunta>?
A: <Resposta>

Q: <Pergunta>?
A: <Resposta>

Q: <Nova pergunta>?
A:
```

Os exemplos devem demonstrar exatamente labels, capitalizacao, estilo e formato esperados. Exemplos ruins ensinam o comportamento errado e precisam entrar no eval contract como risco.

## Regras de design

1. Defina uma tarefa por prompt; decomponha tarefas grandes em subtarefas antes de recombinar.
2. Use comandos diretos como `Escreva`, `Classifique`, `Resuma`, `Traduza` ou `Ordene`.
3. Coloque a instrucao no inicio e use um separador claro como `###` antes do contexto.
4. Troque limites vagos por criterios mensuraveis, por exemplo: `Use 2 a 3 frases`.
5. Declare labels validos, audiencia, idioma, estilo, comprimento e formato quando forem requisitos.
6. Prefira dizer o comportamento desejado; se houver proibicao, declare tambem a alternativa e o fallback.
7. Preserve o prompt baseline e altere um elemento significativo por candidato.
8. Mantenha o prompt mais curto que passe em todos os gates; detalhe irrelevante consome contexto e pode distrair o modelo.

## Amostragem

- `temperature` menor tende a produzir saidas mais deterministicas, adequadas a tarefas factuais e concisas.
- `temperature` maior tende a aumentar variedade e criatividade.
- `top_p` menor restringe a amostragem; `top_p` maior permite maior diversidade.
- Altere `temperature` **ou** `top_p`, nao ambos no mesmo candidato, para preservar atribuicao causal.
- Registre o valor, modelo e versao exatos em cada Experiment.

Os exemplos introdutorios da fonte usavam o legado `text-davinci-003`, `temperature=0.7` e `top_p=1`. Esses valores nao sao defaults universais nem baseline automatico para outros modelos.

## Contrato de experimento

Para cada iteracao, registre:

```text
Prompt ID/version:
Hipotese da mudanca:
Elemento alterado: instrucao | contexto | exemplo | saida | temperature | top_p
Modelo/provider/version:
Dataset/split/version:
Baseline Experiment:
Candidate Experiment:
Gates de formato e semantica:
Custo/latencia budget:
```

Compare baseline e candidato no mesmo Dataset, split, evaluators e configuracoes, exceto pela variavel explicitamente alterada. Use evaluator deterministico para schema, labels, comprimento, regex, argumentos de tool e outras propriedades mecanicas; reserve LLM-as-judge para semantica com rubrica atomica e calibrada.

## Aplicacoes

- **Resumo**: declare comprimento e informacao que deve ser preservada.
- **Extracao**: nomeie campos e formato exato.
- **Pergunta e resposta**: forneca contexto e um fallback para incerteza.
- **Classificacao**: liste labels e demonstre a grafia exata.
- **Conversacao**: declare papel, tom, audiencia e comportamento esperado.
- **Codigo**: forneca linguagem, schemas, restricoes e contexto relevante.
- **Raciocinio**: decomponha quando a resposta direta falhar e valide o resultado com oraculo independente.

## Evidencia e handoff

O Prompt Engineer entrega prompts versionados, diff entre baseline e candidatos, Experiments reais, resultados por gate/segmento, failures, custo, latencia e limitacoes. Ele pode recomendar um candidato, mas nao emite aprovacao independente; uma promocao exige o `langsmith-evals-auditor`.

## Fontes

- https://www.promptingguide.ai/pt/introduction
- https://www.promptingguide.ai/pt/introduction/settings
- https://www.promptingguide.ai/pt/introduction/basics
- https://www.promptingguide.ai/pt/introduction/elements
- https://www.promptingguide.ai/pt/introduction/tips
- https://www.promptingguide.ai/pt/introduction/examples
