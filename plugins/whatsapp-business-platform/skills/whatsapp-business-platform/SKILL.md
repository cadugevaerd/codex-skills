---
name: whatsapp-business-platform
description: Projeta e opera integrações Meta WhatsApp Business Platform, incluindo Cloud API, Technology Provider, Embedded Signup v4 e Coexistence.
argument-hint: "[objetivo] [business_id=<id>] [waba_id=<id>] [phone_number_id=<id>] [modo=empresa|provider|coexistence|diagnostico]"
---

# WhatsApp Business Platform — Meta Cloud API e Coexistence

Use esta skill para desenhar, configurar, revisar ou diagnosticar integrações oficiais da **WhatsApp Business Platform**. Ela separa corretamente App Meta, portfólio empresarial, WABA, Phone Number ID e número visível; também cobre o modelo multiempresa de Technology Provider, Embedded Signup v4 e uso simultâneo do WhatsApp Business App com Cloud API.

A documentação oficial da Meta é a fonte de verdade. Antes de orientar uma configuração real, consulte `references/official-meta-sources.md`; não suponha que versões, permissões, limites, telas ou elegibilidade continuam iguais.

## Quando usar

- Criar um App Meta com caso de uso WhatsApp.
- Verificar ou concluir status de Technology Provider.
- Projetar SaaS multi-tenant para várias WABAs e números.
- Implementar Embedded Signup v4.
- Manter WhatsApp Business App e Cloud API no mesmo número (Coexistence).
- Configurar tokens, webhooks, templates e envio de mensagens.
- Diagnosticar confusão entre App ID, Business ID, WABA ID e Phone Number ID.

## Princípios não negociáveis

1. **Um App Provider não fica fixado a um número.** O App integra várias empresas; cada empresa continua proprietária de sua WABA e Phone Number IDs.
2. **Não confunda ativos.** Um identificador numérico isolado não prova seu tipo.
3. **Coexistence não é toggle comum.** Ela usa onboarding oficial de usuários do WhatsApp Business App via Embedded Signup.
4. **Nunca peça token em chat.** Use cofre de segredos e injete a credencial sem imprimir, versionar ou incluir em argumentos/logs.
5. **Não registre novamente número de Coexistence.** Nesse modo o número já está registrado.
6. **Não invente sucesso.** App Review, verificação empresarial, webhooks e mensagens precisam de evidência real.
7. **Falhe fechado.** Se o token não lê a WABA/Phone Number ID, reporte falta de autorização; não conclua que o ativo inexiste.

## Modelo de ativos

```text
Portfólio empresarial do Provider
└─ App Meta (Technology Provider)
   ├─ Embedded Signup v4
   ├─ callback OAuth / troca de código
   └─ webhook central
      ├─ Cliente A → Business A → WABA A → Phone Number ID A1, A2...
      ├─ Cliente B → Business B → WABA B → Phone Number ID B1...
      └─ Cliente C → Business C → WABA C → Phone Number ID C1...
```

| Objeto | Responsabilidade | Não confundir com |
|---|---|---|
| App ID | software/integrador | WABA ID ou Phone Number ID |
| Business/Portfolio ID | portfólio empresarial Meta | App ID |
| WABA ID | conta WhatsApp Business da empresa | número de telefone |
| Phone Number ID | ativo técnico usado na Graph API | número E.164 |
| Número E.164 | número visível | Phone Number ID |
| Access token | autorização no escopo concedido | ID de ativo |

## Escolha do modo

| Objetivo | Caminho |
|---|---|
| Automatizar somente WABA própria | Cloud API; Technology Provider pode ser desnecessário |
| Integrar WABAs de clientes | Technology Provider ou Solution Partner |
| App manual + automação no mesmo número | Coexistence via Embedded Signup personalizado |
| Operar clientes sem Provider confirmado | Solution Partner compatível |

Antes de recomendar arquitetura, confirme proprietário do número, uso atual do Business App, WABA/Phone Number ID, controlador do token e se o objetivo é uso próprio ou onboarding de clientes.

## Verificar Technology Provider

No App Meta que fornecerá o serviço:

```text
Painel de Apps
→ Casos de uso
→ Personalizar (lápis)
→ WhatsApp → Personalizar
→ Integração do Provedor de Tecnologia
```

Exija evidência de:

- empresa verificada e vinculada ao App;
- App Review aprovado;
- **Advanced Access** para `whatsapp_business_messaging`;
- **Advanced Access** para `whatsapp_business_management`.

Essas permissões permitem enviar em nome de clientes e acessar WABAs que não pertencem à empresa do Provider. Um App WhatsApp ou WABA própria, isoladamente, não prova status de Technology Provider.

## Embedded Signup v4

Para trabalho novo, use v4. A v2 tem descontinuação anunciada para **15 de outubro de 2026**; confirme a data atual antes de repeti-la.

```text
Painel de Apps
→ Login do Facebook para Empresas
→ Configurações
→ Criar configuração
→ Variação: Cadastro Incorporado
→ Selecionar produtos, incluindo Cloud API
→ Copiar Configuration ID
```

Para cada empresa, o fluxo:

1. autentica administrador empresarial e coleta consentimento;
2. seleciona/cria portfólio e WABA conforme elegibilidade;
3. seleciona/adiciona número;
4. concede ao App acesso aos ativos;
5. retorna IDs e código temporário;
6. exige troca servidor-a-servidor por token empresarial;
7. exige inscrição do App nos webhooks da WABA.

Technology Providers usam **business tokens** no onboarding. Guarde por tenant somente referência segura à credencial.

### Estado mínimo por tenant

```json
{
  "tenant_id": "internal-stable-id",
  "business_id": "<BUSINESS_ID>",
  "waba_id": "<WABA_ID>",
  "phone_number_ids": ["<PHONE_NUMBER_ID>"],
  "token_secret_ref": "<SECRET_MANAGER_REFERENCE>",
  "onboarding_mode": "cloud_api|coexistence",
  "status": "pending|active|offboarded|reconnecting|blocked"
}
```

Não use WABA ID ou Phone Number ID como identidade exclusiva do tenant. Preserve isolamento, idempotência e auditoria.

## Coexistence: Business App + Cloud API

Use quando a empresa já utiliza **WhatsApp Business App** e quer manter atendimento manual no mesmo número da automação.

Requisitos documentados:

- WhatsApp Business App `2.24.17` ou posterior;
- onboarding por Solution Partner ou Technology Provider;
- callback capaz de processar webhooks;
- Embedded Signup com registro de sessão;
- launch payload personalizado:

```javascript
{
  "config_id": "<CONFIGURATION_ID>",
  "response_type": "code",
  "override_default_response_type": true,
  "extras": {
    "setup": {},
    "featureType": "whatsapp_business_app_onboarding",
    "sessionInfoVersion": "3"
  }
}
```

O fluxo deve oferecer **conectar conta existente do WhatsApp Business**. A empresa recebe mensagem oficial do Facebook no App, confirma conexão e decide se compartilha contatos/histórico.

Evento esperado no listener:

```javascript
{
  data: { waba_id: "<CUSTOMER_WABA_ID>" },
  type: "WA_EMBEDDED_SIGNUP",
  event: "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING",
  version: 3
}
```

Após concluir:

- capture WABA ID e código temporário;
- troque o código por token empresarial;
- integre WABA e webhooks;
- **não registre o número novamente**;
- inicie sincronização autorizada em até 24 horas;
- mantenha o Business App aberto durante sincronização.

### Verificar status

```http
GET https://graph.facebook.com/<GRAPH_API_VERSION>/<PHONE_NUMBER_ID>?fields=is_on_biz_app,platform_type
Authorization: Bearer <ACCESS_TOKEN>
```

Confirmação positiva:

```json
{
  "is_on_biz_app": true,
  "platform_type": "CLOUD_API",
  "id": "<PHONE_NUMBER_ID>"
}
```

`Unsupported get request` também pode significar token do App errado ou permissão ausente; não prova inexistência.

### Efeitos operacionais

- mensagens 1:1 podem ser espelhadas entre API e App;
- histórico 1:1 de até seis meses pode ser sincronizado;
- grupos não sincronizam;
- mensagens temporárias, visualização única, localização ao vivo e listas de transmissão têm limitações;
- dispositivos complementares são desvinculados e os compatíveis devem ser ligados novamente;
- WhatsApp para Windows e WearOS têm restrições documentadas como complementares;
- throughput de Coexistence é documentado em **20 mps**;
- mensagens pelo App são gratuitas; API segue precificação Cloud API;
- janela de 24 horas aplica-se à API; mensagens do App não criam, estendem ou alteram a janela.

Reconfirme tudo antes de migração: limites de produto mudam.

## Webhooks e handoff humano

Use HTTPS, validação do callback e idempotência por evento/mensagem. Assine cada WABA e roteie por WABA ID + Phone Number ID.

### Validação obrigatória da assinatura

Antes de interpretar JSON, alterar estado ou enfileirar o evento:

1. preserve os **bytes brutos** do corpo HTTP;
2. leia `X-Hub-Signature-256` e exija o prefixo `sha256=`;
3. calcule HMAC-SHA256 do corpo bruto usando o **App Secret** mantido no secret manager;
4. compare a assinatura recebida e a calculada em **tempo constante**;
5. rejeite assinatura ausente ou inválida sem processar o payload;
6. só então desserialize, deduplique e confirme rapidamente o recebimento.

Nunca calcule a assinatura sobre JSON reserializado. Não registre App Secret, assinatura completa nem corpo com PII.

| Campo | Uso |
|---|---|
| `history` | histórico anterior autorizado |
| `smb_app_state_sync` | contatos alterados no Business App |
| `smb_message_echoes` | mensagens enviadas manualmente pelo App/dispositivo compatível |
| `account_update` | lifecycle, offboarding, reconexão, restrições e violações |

### Estado de `account_update`

Mantenha uma máquina de estados idempotente por WABA/tenant:

| Evento/classe | Transição mínima |
|---|---|
| `PARTNER_REMOVED` | revogar vínculo local, suspender envio e iniciar offboarding seguro |
| `ACCOUNT_OFFBOARDED` | marcar `offboarded`, suspender automações e invalidar acesso operacional |
| `ACCOUNT_RECONNECTED` | marcar `revalidation_required`; revalidar WABA, número, permissões, token e webhook antes de reativar |
| restrição, violação ou bloqueio | marcar `restricted`, impedir envio e abrir diagnóstico/auditoria |
| alteração de permissões, tier ou configuração | atualizar capacidades somente após leitura confirmatória da API |
| evento desconhecido | registrar tipo sanitizado e versão, manter idempotência e agir **fail-closed** para operações de envio |

Não reative automaticamente apenas por nome de evento; confirme o estado atual por API oficial e preserve trilha de auditoria.

Todos os clientes podem compartilhar o webhook padrão do App se o backend isola tenants deterministicamente. Use override por WABA/número apenas com requisito explícito.

Ao receber `smb_message_echoes`, registre atendimento humano e aplique a política definida pelo produto: pausa temporária ou liberação explícita. Documente SLA, expiração, prioridade e corrida; não invente regra universal.

## Mensagens e templates

```http
POST https://graph.facebook.com/<GRAPH_API_VERSION>/<PHONE_NUMBER_ID>/messages
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json
```

```json
{
  "messaging_product": "whatsapp",
  "to": "<WHATSAPP_USER_PHONE_NUMBER>",
  "type": "template",
  "template": {
    "name": "hello_world",
    "language": {"code": "en_US"}
  }
}
```

Antes de envio real, confirme destinatário, opt-in, template, janela, finalidade e impacto externo. `POST /messages` tem efeito real. **Nunca execute envio, template de teste, marcação como lida ou outra mutação sem confirmação explícita do usuário para aquele destinatário e ambiente.** Sem confirmação, produza somente plano, payload redigido ou chamada `GET` de diagnóstico.

## Limites e propriedade

- Embedded Signup começa com até 10 novos clientes em sete dias.
- Após verificação empresarial, App Review e verificação de acesso, a Meta documenta 200 novos clientes em sete dias.
- Clientes são proprietários das WABAs/números e mantêm acesso ao WhatsApp Manager.
- WABAs originalmente criadas pelo App do desenvolvedor podem não ser selecionáveis diretamente no Embedded Signup.
- Provider sem Solution Partner exige que o cliente adicione pagamento à própria WABA.

Confirme limites e elegibilidade nas fontes oficiais em cada projeto.

## Segurança

- token em secret manager/1Password/Vault/KMS, nunca `.env` versionado;
- troca OAuth somente no backend;
- valide `state` e associe ao tenant correto;
- least privilege e rotação;
- assinatura de webhook segundo documentação vigente;
- deduplicação e idempotência;
- política explícita para PII em logs;
- ownership antes de aceitar IDs fornecidos pelo cliente;
- suspenda automação em lifecycle incompatível com `active`.

## Procedimento

1. Identifique modo: própria empresa, Provider, parceiro ou Coexistence.
2. Confirme IDs por fonte verificável; não deduza por formato.
3. Consulte fontes oficiais atuais.
4. Desenhe App → Businesses → WABAs → Phone Number IDs.
5. Liste verificação, App Review, permissões e webhooks.
6. Defina token lifecycle, isolamento e offboarding.
7. Planeje Embedded Signup v4 e callback servidor-a-servidor.
8. Em Coexistence, cubra consentimento, sincronização, echoes e dispositivos.
9. Defina testes sem ações externas não autorizadas.
10. Faça chamadas somente leitura antes de mensagem real.

## Formato de saída

```markdown
# WhatsApp Business Platform — plano/diagnóstico
## Status — READY | PARTIAL | BLOCKED
## Modo escolhido
## Evidências — fontes, IDs tipados, permissões e status
## Arquitetura — App → Businesses → WABAs → Phone Number IDs → webhooks
## Configuração necessária
## Procedimento numerado
## Verificação
## Riscos e bloqueios
```

## Verificação final

- [ ] IDs não foram misturados.
- [ ] App Provider não foi modelado como preso a um número.
- [ ] Cada cliente preserva ownership.
- [ ] Embedded Signup e Coexistence usam versão/feature type vigentes.
- [ ] Advanced Access e empresa verificada têm evidência.
- [ ] Tokens e PII não aparecem na saída.
- [ ] Webhooks cobrem multi-tenant, idempotência e lifecycle.
- [ ] Nenhuma ação externa foi inventada ou executada sem autorização.
- [ ] Limitações e versões foram reconfirmadas oficialmente.
