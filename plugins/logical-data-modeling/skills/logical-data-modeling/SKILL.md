---
name: logical-data-modeling
description: "Projeta e revisa modelos lógicos de dados para aplicações relacionais transacionais e Analytics/BI, com regras de integridade, governança, privacidade e plano de validação."
argument-hint: "<domínio, objetivo, fontes, consumidores, volume e restrições conhecidas>"
---

# Modelagem Lógica de Dados

Use esta skill para criar ou revisar um **modelo lógico de dados** para:

- aplicações relacionais e transacionais;
- warehouse, Analytics, BI e dashboards;
- uma arquitetura com separação explícita entre OLTP e camada analítica.

O objetivo é produzir um modelo revisável: entidades, relações, regras, governança e validação. Um diagrama é explicação; o dicionário, as regras e os testes propostos são o contrato.

## Limites inegociáveis

- Não misture modelo transacional e analítico para reduzir quantidade de tabelas. Se ambos forem necessários, modele as camadas e a passagem OLTP → analítica separadamente.
- Não gere, execute ou aplique DDL, migration, alteração de dados ou acesso a banco real por padrão.
- Só rascunhe DDL quando o usuário pedir, informar o SGBD/dialeto e aprovar a passagem do lógico para o físico. DDL continua sendo rascunho até revisão humana explícita.
- Não use credenciais, segredos, registros reais de clientes ou PII desnecessária em exemplos. Use dados sintéticos.
- Não invente base legal, classificação, retenção, roles, ownership ou regras de negócio. Marque como `PENDENTE` quando não informado.

## 1. Triagem: escolha uma arquitetura antes de modelar

Declare uma das opções abaixo na primeira linha da resposta:

1. `Modo: transacional-relacional` — sistema operacional com escrita, consistência e regras de negócio.
2. `Modo: analitico-bi` — consulta, métricas, BI, dashboards ou warehouse.
3. `Modo: oltp-para-analitico` — os dois existem, com modelos distintos e integração/linhagem definida.

Se a escolha não estiver clara, faça no máximo 5 perguntas que realmente mudem o modelo. Caso contrário, declare suposições explícitas e avance.

Perguntas prioritárias:

1. Qual decisão ou processo o modelo precisa suportar, e quem o consome?
2. É escrita operacional, análise histórica, ou ambos em camadas separadas?
3. Quais eventos/processos, fontes e horizonte histórico existem?
4. Há PII, dados financeiros, dados regulados ou restrições de residência/retenção?
5. Qual é o dono de negócio, steward técnico e critérios de sucesso?

## 2. Fluxo transacional-relacional

Modele primeiro os fatos do domínio e suas regras, não telas ou endpoints.

1. Identifique entidades, responsabilidades e limites de agregado.
2. Declare chave primária/candidata, identidade de negócio, atributos obrigatórios e relacionamentos com cardinalidade e opcionalidade.
3. Normaliza até eliminar redundância e anomalias de atualização, salvo desnormalização justificada por uma leitura medida.
4. Registre invariantes no local mais próximo do dado: unicidade, obrigatoriedade, domínio, exclusividade, estados válidos e comportamento de exclusão/atualização.
5. Separe dados sensíveis em atributos/entidades com propósito, acesso e ciclo de vida explícitos.

Para cada relacionamento, diga `1:1`, `1:N` ou `N:N`; para N:N, modele a entidade associativa e suas regras. Não esconda a cardinalidade em narrativa.

## 3. Fluxo analitico-bi

Siga esta ordem: **processo de negócio → grão → dimensões → fatos → métricas**.

1. Declare o processo e o grão de cada tabela fato em uma frase verificável, por exemplo: `uma linha por item de pedido confirmado`.
2. Nunca misture grãos em uma mesma fato. Separe fatos transacionais, snapshots periódicos e acumulativos quando tiverem grãos diferentes.
3. Liste dimensões, chaves de negócio, chaves substitutas quando aplicável, papéis de data e dimensões conformadas reutilizadas entre fatos.
4. Para cada medida, declare unidade, fórmula, fonte, janela temporal e comportamento `aditiva`, `semiaditiva` ou `não aditiva`.
5. Defina estratégia de histórico/SCD quando atributos dimensionais mudam; se não houver decisão, registre `PENDENTE` em vez de presumir SCD Tipo 2.
6. Diferencie modelo de warehouse e camada semântica: métricas certificadas, nomes de negócio, filtros e relações de BI são entregas próprias.

Não trate filtros de dashboard como controle de segurança. Acesso a linhas e colunas deve ser especificado como política aplicável no armazenamento, views, camada semântica ou todos os pontos necessários.

## 4. Segurança, privacidade e governança

Inclua a matriz abaixo para atributos sensíveis e para qualquer atributo cuja classificação seja desconhecida:

| Dado/campo | Classificação | Finalidade | Dono/steward | Papéis autorizados | Proteção | Retenção/eliminação | Linhagem/auditoria |
|---|---|---|---|---|---|---|---|
| ... | Pública / Interna / Confidencial / Regulada / PENDENTE | ... | ... | ... | mascaramento, tokenização, RLS/CLS ou PENDENTE | ... | ... |

Aplique minimização: se um atributo sensível não é indispensável para o objetivo, proponha removê-lo ou substituí-lo por derivação/agregação. Para dados sensíveis, descreva acesso por papel, segregação de deveres, mascaramento/tokenização quando aplicável, logs de acesso/exportação e plano de retenção/eliminação.

## 5. Contrato de saída obrigatório: HTML único e autocontido

A resposta final deve ser **exatamente um documento HTML completo** — comece em `<!doctype html>` e termine em `</html>`. Não acrescente explicações, Markdown ou blocos de código antes ou depois.

Regras de entrega:

- Inclua todo CSS em um único bloco `<style>` e todo JavaScript em um único bloco `<script>` no mesmo arquivo. Não use CDN, fontes remotas, imagens externas, iframes, bibliotecas ou build step.
- Produza HTML semântico (`header`, `nav`, `main`, `section`, `details`, `table`, `footer`), responsivo e navegável por teclado.
- Não injete texto não confiável com `innerHTML`; a interação deve operar apenas sobre elementos já gerados no documento.
- Use cores como apoio, nunca como único sinal. Garanta foco visível, contraste adequado e `@media (prefers-reduced-motion: reduce)` para remover animações.
- Não use dados reais, segredos ou PII nos exemplos. Quando faltar contexto, escreva `PENDENTE` de forma visível.

O documento precisa ser legível rapidamente e conter, nesta ordem:

1. **Cabeçalho:** nome do modelo, modo, status, data de geração, escopo e um resumo de decisões.
2. **Navegação de leitura:** links para as seções; indicador de progresso da leitura; controles `Expandir seções` e `Recolher seções`.
3. **Escopo e pendências:** incluído, fora de escopo, suposições e bloqueios para produção.
4. **Visão do modelo:** diagrama ER com SVG inline ou representação textual acessível; não dependa de Mermaid remoto ou renderização externa.
5. **Dicionário lógico:** tabela responsiva com entidade, finalidade, chave/identidade, atributos/domínios, relações e regras de integridade.
6. **Regras e ciclo de vida.**
7. **Governança e segurança:** matriz com classificação, finalidade, owner/steward, papéis, proteção, retenção/eliminação e linhagem/auditoria.
8. **Contrato analítico** quando o modo for `analitico-bi` ou `oltp-para-analitico`: fato/métrica, processo e grão, dimensões, aditividade, fonte, histórico, consumidores e métricas certificadas.
9. **Validação proposta, decisões/riscos, anti-padrões e aprovações necessárias.**

Inclua interações leves que ajudem a leitura, não decoração:

- nav fixa/pegajosa com progresso calculado no scroll;
- seções em `<details>` com resumo objetivo e opção global de expandir/recolher;
- destaque visual da seção ativa;
- botão para alternar foco de leitura (oculta temporariamente seções secundárias);
- entradas animadas discretamente apenas quando `prefers-reduced-motion` permitir.

Use esta base e substitua todos os marcadores por conteúdo real do modelo:

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Modelo lógico — NOME_DO_MODELO</title>
  <style>
    :root { color-scheme: light dark; --bg:#0b1020; --surface:#151c31; --text:#edf2ff; --muted:#b7c2df; --accent:#74d9b8; --warn:#ffd166; --danger:#ff8b94; --ring:#fff; }
    * { box-sizing:border-box; }
    html { scroll-behavior:smooth; }
    body { margin:0; background:var(--bg); color:var(--text); font:16px/1.55 system-ui,sans-serif; }
    .shell { max-width:1200px; margin:auto; padding:1.25rem; }
    .hero, section, details { background:var(--surface); border:1px solid #ffffff1f; border-radius:14px; padding:1rem; margin-block:1rem; }
    nav { position:sticky; top:0; z-index:2; background:#0b1020ed; backdrop-filter:blur(8px); padding:.75rem 0; }
    nav a, button { color:var(--text); background:transparent; border:1px solid #ffffff35; border-radius:8px; padding:.4rem .65rem; cursor:pointer; }
    nav a[aria-current="true"], button:focus-visible, a:focus-visible { outline:3px solid var(--ring); outline-offset:2px; background:#ffffff18; }
    .progress { height:4px; background:#ffffff22; border-radius:2px; } .progress > i { display:block; width:0; height:100%; background:var(--accent); border-radius:inherit; }
    .meta, .chips { display:flex; flex-wrap:wrap; gap:.5rem; } .chip { border:1px solid #ffffff35; border-radius:999px; padding:.15rem .6rem; color:var(--muted); }
    table { width:100%; border-collapse:collapse; } th,td { border-bottom:1px solid #ffffff25; padding:.65rem; text-align:left; vertical-align:top; } .table-wrap { overflow:auto; }
    .active { border-color:var(--accent); box-shadow:0 0 0 1px var(--accent); } .pending { color:var(--warn); } .risk { color:var(--danger); }
    [data-secondary].reading-focus { display:none; } .reveal { animation:reveal .35s ease both; } @keyframes reveal { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:none } }
    @media (max-width:700px) { .shell { padding:.75rem; } nav { overflow:auto; white-space:nowrap; } th,td { min-width:10rem; } }
    @media (prefers-reduced-motion:reduce) { html { scroll-behavior:auto; } *,*::before,*::after { animation:none!important; transition:none!important; } }
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero reveal"><p class="chip">MODO_DO_MODELO</p><h1>NOME_DO_MODELO</h1><p>Resumo de decisões: RESUMO_REAL.</p><div class="meta"><span>Escopo: ESCOPO_REAL</span><span>Status: rascunho para revisão humana</span><span>Gerado: DATA</span></div></header>
    <nav aria-label="Navegação do modelo"><div class="progress" aria-label="Progresso de leitura"><i id="progress"></i></div><p><a href="#escopo">Escopo</a> <a href="#modelo">Modelo</a> <a href="#dados">Dicionário</a> <a href="#governanca">Governança</a> <a href="#validacao">Validação</a> <button type="button" id="expand">Expandir seções</button> <button type="button" id="collapse">Recolher seções</button> <button type="button" id="focus">Foco de leitura</button></p></nav>
    <main>
      <section id="escopo" class="reveal"><h2>Escopo, suposições e pendências</h2><ul><li>Incluído: CONTEÚDO_REAL</li><li>Fora de escopo: CONTEÚDO_REAL</li><li>Suposições: CONTEÚDO_REAL</li><li class="pending">Pendências que bloqueiam produção: CONTEÚDO_REAL</li></ul></section>
      <section id="modelo" class="reveal"><h2>Visão do modelo</h2><div role="img" aria-label="Diagrama entidade-relacionamento: DESCRIÇÃO_REAL">DIAGRAMA_SVG_INLINE_OU_REPRESENTAÇÃO_TEXTUAL_ACESSÍVEL</div></section>
      <section id="dados" class="reveal"><h2>Dicionário lógico de dados</h2><div class="table-wrap"><table><thead><tr><th>Entidade</th><th>Finalidade</th><th>Chave/identidade</th><th>Atributos e domínios</th><th>Relações</th><th>Regras</th></tr></thead><tbody>LINHAS_REAIS</tbody></table></div></section>
      <details open class="reveal"><summary><strong>Regras e ciclo de vida</strong></summary><p>CONTEÚDO_REAL</p></details>
      <section id="governanca" class="reveal"><h2>Governança e segurança</h2><div class="table-wrap"><table><thead><tr><th>Dado/campo</th><th>Classificação</th><th>Finalidade</th><th>Owner/steward</th><th>Papéis</th><th>Proteção</th><th>Retenção</th><th>Linhagem/auditoria</th></tr></thead><tbody>LINHAS_REAIS</tbody></table></div></section>
      <section id="analitico" data-secondary class="reveal"><h2>Contrato analítico</h2><p>Inclua somente nos modos analitico-bi e oltp-para-analitico. Declare grão, dimensões, aditividade, histórico e risco de dupla contagem para cada fato/métrica.</p><div class="table-wrap"><table><thead><tr><th>Fato/métrica</th><th>Processo e grão</th><th>Dimensões</th><th>Aditividade</th><th>Fonte/linhagem</th><th>Histórico</th><th>Consumidores</th></tr></thead><tbody>LINHAS_REAIS_OU_REMOVA_A_SEÇÃO</tbody></table></div></section>
      <section id="validacao" class="reveal"><h2>Validação, riscos e aprovações</h2><details open><summary>Validações propostas</summary><ul><li>Estrutural: CONTEÚDO_REAL</li><li>Qualidade/reconciliação: CONTEÚDO_REAL</li><li>Segurança: CONTEÚDO_REAL</li><li>Compatibilidade/migração: CONTEÚDO_REAL</li></ul></details><details><summary>Decisões, riscos e anti-padrões</summary><p>CONTEÚDO_REAL</p></details><details><summary>Aprovação antes da implementação física</summary><ul><li>[ ] Dono de negócio</li><li>[ ] Steward/dono técnico</li><li>[ ] Segurança/privacidade quando aplicável</li><li>[ ] Revisão de DDL/migration e rollback quando houver mudança real</li></ul></details></section>
    </main>
    <footer><small>Modelo lógico — rascunho sujeito a revisão humana.</small></footer>
  </div>
  <script>
    const sections = [...document.querySelectorAll('main > section, main > details')];
    const details = [...document.querySelectorAll('details')];
    const setDetails = open => details.forEach(item => item.open = open);
    document.querySelector('#expand').onclick = () => setDetails(true);
    document.querySelector('#collapse').onclick = () => setDetails(false);
    document.querySelector('#focus').onclick = event => { document.querySelectorAll('[data-secondary]').forEach(item => item.classList.toggle('reading-focus')); event.currentTarget.setAttribute('aria-pressed', String(event.currentTarget.getAttribute('aria-pressed') !== 'true')); };
    addEventListener('scroll', () => { const max = document.documentElement.scrollHeight - innerHeight; document.querySelector('#progress').style.width = `${max ? scrollY / max * 100 : 0}%`; }, {passive:true});
    const observer = new IntersectionObserver(entries => entries.forEach(({target,isIntersecting}) => { if (isIntersecting) { sections.forEach(s => s.classList.toggle('active', s === target)); document.querySelectorAll(`nav a`).forEach(a => a.setAttribute('aria-current', String(a.getAttribute('href') === `#${target.id}`))); } }), {rootMargin:'-20% 0px -70%'});
    sections.forEach(section => observer.observe(section));
  </script>
</body>
</html>
```

A base é um contrato de estrutura, não conteúdo a ser deixado com marcadores. Remova a seção `#analitico` quando o modo for exclusivamente transacional; não adicione seções vazias.

## 6. Plano de validação

Toda modelagem deve propor verificações concretas, sem alegar que foram executadas se não foram.

- **Estrutural:** identidade única; referências válidas; cardinalidade/opcionalidade; domínios; atributos obrigatórios; nenhum identificador duplicado.
- **Transacional:** duplicatas de chave, órfãos, estados inválidos, conflitos de unicidade, nulos proibidos e regras de transição.
- **Analítico:** uma linha por grão declarado, dimensões conformadas consistentes, chaves órfãs, datas inválidas, períodos efetivos sobrepostos, reconciliação com fontes e detecção de dupla contagem.
- **Segurança:** tentativa de leitura por papel não autorizado, exposição por coluna/linha, exportação e auditoria de acesso sensível.
- **Mudanças físicas solicitadas:** compatibilidade com consumidores, backfill, bloqueios, reversibilidade e aprovação humana antes da execução.

Prefira restrições nativas do banco para invariantes persistidos; a aplicação e o BI não são a única linha de defesa. Quando o alvo físico for conhecido e solicitado, marque claramente quais regras viram PK, FK, UNIQUE, NOT NULL, CHECK, RLS/CLS, view, teste de qualidade ou controle operacional.

## 7. Revisão contra anti-padrões

Antes de encerrar, confira e registre o resultado:

- [ ] tabela universal/JSON genérico usado para evitar decisão de domínio;
- [ ] PII replicada em fato/dimensão sem finalidade e proteção;
- [ ] relação N:N sem entidade associativa;
- [ ] chave técnica sem identidade de negócio ou regra de deduplicação;
- [ ] fato sem grão, métrica sem fórmula ou medida de grãos mistos;
- [ ] dimensão não conformada para conceito compartilhado;
- [ ] regra de integridade apenas na aplicação;
- [ ] BI/dashboard usado como fronteira de segurança;
- [ ] DDL/migration tratado como aprovado sem revisão humana.

## Referências de projeto

Use como critérios técnicos, não como substituto da regra de negócio:

- Kimball Group: [Four-Step Dimensional Design](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/four-4-step-design-process/) e [Grain](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/grain/).
- PostgreSQL: [Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html).
- dbt: [Data tests](https://docs.getdbt.com/docs/build/data-tests).
- OWASP: [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html).
- NIST: [SP 800-53](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) e [Privacy Framework](https://www.nist.gov/privacy-framework).
