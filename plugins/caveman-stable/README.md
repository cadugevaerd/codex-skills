# caveman-stable

Plugin Codex de estilo de saída curto, direto e estável. Sempre ativo enquanto habilitado e com o hook confiado; não anuncia seu próprio funcionamento.

## Instalação e confiança

A partir do GitHub:

```bash
codex plugin marketplace add cadugevaerd/codex-skills --ref main
codex plugin add caveman-stable@codex-skills
```

Para desenvolvimento local, substitua a primeira linha por `codex plugin marketplace add .` na raiz do clone.

Revise e confie o hook em `/hooks` antes de usar. O injetor requer Python 3, não usa dependências externas e recebe JSON por stdin. O contrato é lido somente de `PLUGIN_ROOT`; nenhum estado ou arquivo do repositório é gravado.

A entrada `SessionStart` usa o matcher `startup|resume|clear|compact`. A inclusão de `compact` reinjeta o contrato após compactação automática ou manual.

Para rollback, desative ou desinstale o plugin e verifique `/hooks` novamente.

## Comportamento

Mantém o idioma dominante, remove filler, pleasantries, hedging, repetição e narração rotineira, preserva artefatos técnicos exatamente e usa prosa explícita para segurança, destruição, ambiguidade e passos. Só a forma muda; escopo, ferramentas, permissões e verificação permanecem intactos.

## Estrutura

```text
plugins/caveman-stable/
├── .codex-plugin/plugin.json
├── hooks/hooks.json
├── hooks/inject_context.py
├── skills/caveman-stable/SKILL.md
├── skills/caveman-stable/references/output-contract.md
├── UPSTREAM.md
├── tests/shared-files.sha256
└── tests/validate_contract.py
```

## Atribuição

O conceito de concisão foi inspirado por `JuliusBrussee/caveman`, distribuído sob MIT. Esta implementação é independente e não inclui código-fonte ou texto substancial do upstream. Veja `UPSTREAM.md`.
