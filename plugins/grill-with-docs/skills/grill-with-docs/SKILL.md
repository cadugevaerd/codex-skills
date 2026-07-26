---
name: grill-with-docs
description: Entrevista decisões arquiteturais uma por vez e mantém documentação auditável.
---
# Grill with Docs

Use este protocolo para transformar uma conversa de arquitetura em decisões rastreáveis. Trabalhe no repositório real e escreva os artefatos no momento da decisão; não alegue verificação sem fonte.

## Descoberta e rodada
1. Classifique o cenário como **brownfield**, **greenfield com autoridade externa** ou **greenfield com EVIDENCE GAP**. Em greenfield, busque documentação oficial vigente e registre título, URL, versão/data, seção e consulta. Blog ou memória não substituem fonte oficial.
2. Classifique cada afirmação como `official-doc`, `code`, `test`, `existing-adr`, `user-decision` ou `inference`, e estado `verified`, `partial` ou `unverified`.
3. Faça exatamente uma pergunta atômica. Sempre apresente Evidência, Recomendação, Opções e a pergunta. Cada opção, inclusive a recomendada, declara custo de implementação, operação e reversão/lock-in quando aplicável.
4. Desafie termos vagos; proponha termo canônico e termos evitados e atualize `CONTEXT.md` inline. Esse arquivo é apenas glossário.

## Registro
- Se ADR foi solicitado como produto, registre cada decisão arquitetural substantiva ao fechar, sem oferecê-lo repetidamente. Caso contrário, só crie ADR se for difícil de reverter, surpreendente sem contexto e houver trade-off real.
- ADR gerenciado vive em `docs/adr/` (o auditor também lê `adrs/` legado), usa `managed-by: grill-with-docs/v1`, status `proposed|conditional|accepted|superseded|deprecated`, evidência e fontes. `accepted` nunca depende silenciosamente de `unverified`; transforme em `conditional` e crie/linke `BL-NNNN`.
- Adiamento exige pergunta, motivo, impacto, evidência necessária, responsável, gatilho de retomada e ponto de parada.
- Emenda, exceção e substituição são uma única ação: classifique impacto, atualize antigo, crie/atualize novo, backlinks nos dois sentidos, CONTEXT/backlog/ROADMAP e audite. Substituição deixa antigo `superseded` e nunca dois `accepted` conflitantes.
- Nova evidência dispara impact scan em ordem: termos → ADRs → BLs → ROADMAP → dependências. Reabra, emende ou substitua o que for afetado.
- Crie ROADMAP apenas quando houver dependência, bloqueio adiado ou pedido de sequenciamento. Cada etapa referencia ADR/BL, dependências, entrada, saída e estado.

## Auditoria e parada
Audite a cada 5 ADRs novos/alterados, após pivô/emenda/exceção/substituição, ao encerramento e antes da resposta final. Use `scripts/audit_decisions.py <diretório>`; ele é fail-closed, valida estritamente apenas ADRs marcados `managed-by: grill-with-docs/v1` e não quebra ADRs legados. Relate mecânica e semântica, achados, escopo e veredito `GO`, `NO-GO` ou `BLOCKED`.

Só declare STOP por saturação comprovada: fronteira material vazia; tudo registrado ou adiado; todo desconhecido tem evidência e gatilho; auditoria passa; segunda passada não cria pergunta/ADR/BL de alto impacto; restantes são reversíveis e recebem default documentado.

Templates em `assets/`; protocolo detalhado e atribuição em `references/`.
