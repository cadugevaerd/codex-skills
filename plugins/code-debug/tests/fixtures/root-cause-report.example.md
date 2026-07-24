# Relatório de debug

## Status
Causa raiz comprovada.

## Sintoma reproduzido
- Comando/cenário: `python -m pytest tests/test_config.py -q`
- Resultado observado: exit code 1 ao carregar configuração inválida.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| Exceção antes da validação | `stderr` do teste | A falha ocorre durante a leitura da configuração. |
| Valor inválido reproduz a exceção | teste mínimo isolado | A entrada controla deterministicamente o sintoma. |

## Caminho de investigação/Hipóteses eliminadas
1. Reprodução capturada → falha determinística.
2. Hipótese de ambiente eliminada → mesmo resultado em processo isolado.
3. Hipótese de entrada confirmada → apenas o valor inválido dispara o caminho.

## Causa raiz
A configuração inválida é consumida antes da validação obrigatória.

## Cadeia causal
Configuração inválida → leitura sem validação → exceção → falha do teste.

## Arquivos envolvidos
- `src/config.py`: lê a configuração antes de validá-la.
- `tests/test_config.py`: contém a reprodução mínima.

## Limitações/incertezas
- Nenhuma para o sintoma reproduzido.

Diagnóstico encerrado. Nenhuma correção foi executada.
