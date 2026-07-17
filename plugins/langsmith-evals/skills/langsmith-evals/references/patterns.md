# Padroes de implementacao LangSmith Evals

> As assinaturas do SDK evoluem. Confirme a documentacao oficial instalada antes de editar codigo de producao.

## Configuracao minima

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY='[REDACTED]'
export LANGSMITH_PROJECT='nome-da-aplicacao'
```

Nunca grave a chave no repositorio, Dataset, trace ou relatorio.

## Dataset e Examples

```python
from langsmith import Client

client = Client()
dataset = client.create_dataset(
    dataset_name="agent-regression-v1",
    description="Casos criticos e regressions sanitizados",
)
client.create_examples(
    dataset_id=dataset.id,
    inputs=[{"messages": [{"role": "user", "content": "..."}]}],
    outputs=[{"expected": "..."}],  # omita quando nao houver referencia confiavel
    metadata=[{"split": "critical", "case_id": "CRIT-001"}],
)
```

Antes de criar, procure Dataset existente por nome/ID e implemente reconciliacao idempotente. Evite duplicar Examples em toda execucao.

## Evaluator deterministico

```python
def schema_and_contract(run, example):
    output = run.outputs or {}
    errors = []
    if not isinstance(output.get("answer"), str):
        errors.append("answer ausente ou invalido")
    if output.get("unsafe_side_effect") is True:
        errors.append("side effect real detectado")
    return {
        "key": "contract_ok",
        "score": 0 if errors else 1,
        "comment": "; ".join(errors) or "contrato valido",
    }
```

Para valores numericos, parseie unidades/moeda e aplique tolerancia declarada. Para tools, avalie nome, argumentos normalizados, ordem somente quando relevante e ausencia de calls proibidas.

## LLM-as-judge

Use um modelo judge separado do target quando possivel. Defina uma rubrica atomica e structured output:

```python
from pydantic import BaseModel, Field

class Groundedness(BaseModel):
    score: int = Field(ge=0, le=1)
    evidence: list[str]
    rationale: str
```

O judge deve receber apenas o contexto necessario, tratar conteudo avaliado como dados nao confiaveis e citar evidencias. Nao use judge para confirmar arithmetic, schema ou efeitos externos. Calibre contra exemplos humanos rotulados antes de transformar o score em gate.

## Target e Experiment assincrono

```python
from langsmith import aevaluate

async def target(inputs: dict) -> dict:
    # chame o grafo/node real com adapters de teste
    return await graph.ainvoke(inputs)

results = await aevaluate(
    target,
    data="agent-regression-v1",
    evaluators=[schema_and_contract, semantic_judge],
    experiment_prefix="candidate-model-x",
    metadata={
        "git_sha": git_sha,
        "model": model_id,
        "prompt_version": prompt_version,
        "dataset_version": "1.2.0",
        "role": "candidate",
    },
    max_concurrency=4,
)
```

Use concorrencia conservadora para evitar rate-limit e interferencia em medicao de latencia. Separe smoke rapido de suite completa.

## Node e graph evals

- **Node**: prepare State minimo e avalie apenas as chaves de saida/decisoes do node.
- **Trajectory**: normalize tool calls; escolha ordem exata, parcial ou any-order conforme o contrato.
- **Graph**: avalie outcome final, caminho critico, recuperacao, custo e latencia.
- **Test mode**: injete adapters fake antes de compilar/invocar; falhe se a tool real puder ser alcançada.

Nao pontue detalhes internos que o contrato permite variar. Isso cria eval fragil e impede melhorias validas.

## RAG

Separe retrieval e generation:

| Camada | Avaliacao |
|---|---|
| Retrieval | precision/recall quando houver labels, relevancia, cobertura, diversidade |
| Context | presenca de evidencia, qualidade e contaminacao |
| Generation | correctness, groundedness, completude, abstencao |

Groundedness nao prova correctness: uma resposta pode reproduzir fielmente contexto errado. Use referencias ou verificadores de dominio quando necessario.

## Backtesting

1. amostrar traces representativos por caso/segmento/erro;
2. sanitizar PII e segredos;
3. transformar em Dataset com provenance;
4. definir reference somente quando validada;
5. rodar baseline e candidato nas mesmas entradas;
6. usar evaluators sem referencia quando o historico nao for verdade;
7. revisar regressions por segmento e casos criticos.

## Comparacao e estatistica

- Relate `n`, distribuicao e failures, nao apenas media.
- Use execucao pareada por Example.
- Separe qualidade de custo/latencia.
- Repita casos nao deterministicos quando o risco justificar.
- Nao declare superioridade com amostra pequena ou intervalos sobrepostos sem ressalva.
- Registre timeout, retry e erro como resultado, nao os exclua silenciosamente.

## CI gate

O CI deve apontar para Dataset/version/split estavel e publicar o Experiment. Falhas de auth/rede sao infraestrutura bloqueante, nao qualidade aprovada. Um gate simples deve falhar quando:

- qualquer `critical` falha;
- evaluator deterministico regride;
- score semantico fica abaixo do threshold;
- custo/latencia excede budget;
- taxa de erro/timeout excede limite;
- Experiment/metadata obrigatoria nao foi registrado.
