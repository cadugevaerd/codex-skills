# Pytest Deterministic Patterns

## Escopo

Use Pytest para contratos cujo resultado correto pode ser decidido sem julgamento semantico. Estes testes devem ser rapidos, reproduziveis e executaveis sem LLM, rede ou credenciais sempre que o target permitir.

## Oraculos apropriados

- igualdade exata, tolerancia numerica e propriedades matematicas;
- schema, tipos, campos obrigatorios, enums e serializacao;
- parsers, regex, AST, SQL/DAX gerado e formatos estruturados;
- nome, ordem obrigatoria e argumentos de tool calls;
- transformacoes de State em nodes e invariantes de trajetoria;
- routing, guardrails, autorizacao e contratos de erro;
- idempotencia, ausencia de escrita real e isolamento de side effects;
- custo, latencia ou contagem quando medidos por limites objetivos e ambiente controlado.

Nao use este agente para relevancia, clareza, groundedness sem fonte mecanicamente verificavel, tom ou utilidade. Encaminhe esses criterios ao Engineer para evaluator semantico calibrado.

## Fluxo obrigatorio

1. Leia os contratos do projeto e encontre a menor unidade deterministica testavel. Confirme target, input/output esperado, tolerancias, comportamento proibido, estrategia de fake, comando/escopo Pytest e se `langsmith_feedback` esta habilitado.
2. Declare input, output esperado, invariantes, tolerancias e casos-limite antes de editar.
3. Escreva primeiro um teste que falhe pelo motivo esperado; execute-o e preserve a evidencia da falha.
4. Implemente somente a mudanca minima necessaria quando o pedido incluir correcao.
5. Execute o teste focal, depois o modulo e finalmente a suite relevante.
6. Nao converta dependencia externa em teste instavel: injete fake/adapter, `monkeypatch`, `tmp_path`, clock/UUID/seed fixos e fixtures locais.
7. Reporte comandos, contagens, failures e arquivos alterados. Se faltar expectativa necessaria para decidir o contrato, retorne `BLOCKED`; nunca declare PASS sem output real.

## Padroes Pytest

### Igualdade e tolerancia

```python
import pytest


def test_total_is_stable() -> None:
    assert calculate_total([10.0, 0.1]) == pytest.approx(10.1, abs=1e-9)
```

### Tool call contratual

```python
def test_routes_with_exact_tool_args() -> None:
    call = route_request({"customer_id": "C-42"})
    assert call == {
        "name": "get_customer",
        "args": {"customer_id": "C-42"},
    }
```

### Side effect isolado

```python
def test_dry_run_never_calls_real_gateway(monkeypatch) -> None:
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("real gateway was called")

    monkeypatch.setattr(module.gateway, "send", forbidden)
    result = execute(action, dry_run=True)
    assert result.status == "simulated"
    assert called is False
```

### LangSmith opcional para evidencia

Quando o teste deterministico fizer parte de um Dataset/Experiment, mantenha a assercao Pytest como fonte da decisao e apenas publique inputs, referencias, outputs e feedback:

```python
import pytest
from langsmith import testing as t


@pytest.mark.langsmith
def test_schema_contract() -> None:
    inputs = {"query": "status"}
    expected = {"required": ["status", "items"]}
    actual = target(inputs)
    t.log_inputs(inputs)
    t.log_reference_outputs(expected)
    t.log_outputs(actual)
    passed = all(key in actual for key in expected["required"])
    t.log_feedback(key="schema_contract", score=int(passed))
    assert passed
```

Execute localmente sem publicacao quando o teste nao depende do LangSmith:

```bash
pytest -q tests/path/test_target.py
```

Para casos marcados e credenciais disponiveis:

```bash
pytest --langsmith-output -q tests/path/test_target.py
```

Ausencia de credencial LangSmith nao invalida testes unitarios puros. Ela bloqueia somente a publicacao/Experiment solicitado; reporte essa fronteira explicitamente.

## Anti-padroes

- chamar LLM ou judge para decidir um contrato mecanico;
- snapshots enormes que aprovam mudancas acidentais;
- `sleep`, rede real, ordem global ou horario corrente sem controle;
- mocks que repetem a implementacao em vez de validar o contrato;
- asserts frouxos como `assert result` quando campos especificos importam;
- marcar teste quebrado como `skip`/`xfail` sem criterio e prazo;
- misturar criterios semanticos e deterministicos em uma unica nota.

## Saida do agente

```markdown
# Pytest Deterministic Report

## Status
PASS | FAIL | ERROR | BLOCKED

## Escopo
- Contract/case ID:
- Contratos cobertos:
- Fora de escopo semantico:

## Evidencia TDD
- Falha inicial: comando + resumo
- Implementacao minima:

## Execucao
| Comando | Passed | Failed | Skipped | Duracao |
|---|---:|---:|---:|---:|

## Cobertura de risco
- Edge cases:
- Side effects isolados:
- LangSmith feedback: disabled | published:ID/URL | blocked:motivo
- Promotion decision: NOT_APPLICABLE
- Limitações:
```
