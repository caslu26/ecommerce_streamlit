# Sistema de Pagamento com APIs Reais

Este documento explica como configurar e usar as APIs reais de pagamento integradas ao sistema e-commerce.

## 🚀 Funcionalidades Implementadas

### ✅ Métodos de Pagamento Suportados

- **PIX** - Pagamento instantâneo
- **Cartão de Crédito** - Com parcelamento
- **Cartão de Débito** - À vista com taxa reduzida
- **Boleto Bancário** - Pagamento em banco/lotérica

### ✅ APIs Integradas

- **Stripe** - Gateway internacional
- **PagSeguro** - Gateway brasileiro
- **Mercado Pago** - Gateway latino-americano

## 📋 Configuração

### 1. Configurar APIs de Pagamento

Edite o arquivo `payment_apis_config.json`:

```json
{
  "stripe": {
    "enabled": true,
    "environment": "sandbox",
    "api_key": "sk_test_sua_chave_aqui",
    "secret_key": "sk_test_sua_chave_secreta",
    "webhook_secret": "whsec_seu_webhook_secret"
  },
  "pagseguro": {
    "enabled": true,
    "environment": "sandbox",
    "api_key": "SEU_TOKEN_PAGSEGURO"
  },
  "mercadopago": {
    "enabled": true,
    "environment": "sandbox",
    "api_key": "TEST-sua_chave_publica",
    "access_token": "TEST-seu_access_token"
  }
}
```

### 2. Configurar PIX

No painel administrativo, vá em **Admin > Config Pagamentos > PIX** e configure:

- Chave PIX (CPF, CNPJ, email ou chave aleatória)
- Nome do recebedor
- Cidade

### 3. Configurar Boleto

No painel administrativo, vá em **Admin > Config Pagamentos > Boleto** e configure:

- Banco
- Agência
- Conta
- Nome do cedente
- CNPJ

## 🔧 Como Usar

### Para Desenvolvedores

#### Processar Pagamento com Cartão de Crédito

```python
from payment_system import PaymentProcessor

processor = PaymentProcessor()

card_data = {
    'number': '4111111111111111',
    'expiry': '12/25',
    'cvv': '123',
    'name': 'JOÃO DA SILVA',
    'amount': 100.00,
    'installments': 3
}

result = processor.process_credit_card(card_data)
```

#### Processar Pagamento com Cartão de Débito

```python
card_data = {
    'number': '4111111111111111',
    'expiry': '12/25',
    'cvv': '123',
    'name': 'JOÃO DA SILVA',
    'amount': 100.00
}

result = processor.process_debit_card(card_data)
```

#### Processar Pagamento PIX

```python
pix_data = {
    'amount': 100.00,
    'description': 'Pagamento de pedido #123'
}

result = processor.process_pix(pix_data)
```

### Para Usuários Finais

1. **Adicione produtos ao carrinho**
2. **Vá para o checkout**
3. **Preencha o endereço de entrega**
4. **Escolha o método de pagamento:**
   - **PIX**: Escaneie o QR Code ou use a chave PIX
   - **Cartão de Crédito**: Digite os dados do cartão e escolha o parcelamento
   - **Cartão de Débito**: Digite os dados do cartão (pagamento à vista)
   - **Boleto**: Imprima e pague em qualquer banco

## 🛡️ Segurança

### Validações Implementadas

- **Número do cartão**: Algoritmo de Luhn
- **CVV**: 3-4 dígitos numéricos
- **Data de expiração**: Formato MM/AA válido
- **CPF**: Validação completa
- **Email**: Formato válido

### Boas Práticas

- ✅ Dados do cartão não são armazenados
- ✅ Conexão SSL/TLS obrigatória
- ✅ Validação server-side
- ✅ Logs de transações
- ✅ Webhooks para notificações

## 📊 Monitoramento

### Dashboard Administrativo

Acesse **Admin > Pagamentos** para:

- Ver todas as transações
- Filtrar por status e método
- Aprovar/cancelar pagamentos
- Ver estatísticas de vendas

### Status de Pagamento

- **approved**: Pagamento aprovado
- **pending**: Aguardando pagamento (PIX/Boleto)
- **failed**: Pagamento falhou
- **cancelled**: Pagamento cancelado

## 🔄 Webhooks

Configure webhooks para receber notificações em tempo real:

### Stripe

```bash
curl -X POST https://api.stripe.com/v1/webhook_endpoints \
  -u sk_test_...: \
  -d url=https://seudominio.com/webhook/stripe \
  -d "enabled_events[]=payment_intent.succeeded" \
  -d "enabled_events[]=payment_intent.payment_failed"
```

### PagSeguro

Configure no painel do PagSeguro:

- URL: `https://seudominio.com/webhook/pagseguro`
- Eventos: `PAYMENT`, `TRANSACTION_STATUS_CHANGED`

### Mercado Pago

```bash
curl -X POST https://api.mercadopago.com/v1/webhooks \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://seudominio.com/webhook/mercadopago",
    "events": ["payment"]
  }'
```

## 🧪 Testes

### Cartões de Teste

#### Stripe

- **Sucesso**: 4242424242424242
- **Falha**: 4000000000000002
- **CVV**: Qualquer 3 dígitos
- **Data**: Qualquer data futura

#### PagSeguro

- **Sucesso**: 4111111111111111
- **Falha**: 4000000000000002

#### Mercado Pago

- **Sucesso**: 4509790112684851
- **Falha**: 4000000000000002

## 📈 Taxas

### Taxas Padrão

- **PIX**: Sem taxas
- **Cartão de Crédito**: 2.99% + R$ 0,50
- **Cartão de Débito**: 1.50% + R$ 0,25 (50% de desconto)
- **Boleto**: Sem taxas

### Personalização

Edite `payment_config.json` para ajustar as taxas:

```json
{
  "cartao": {
    "taxa_porcentagem": 2.99,
    "taxa_fixa": 0.5
  }
}
```

## 🚨 Troubleshooting

### Problemas Comuns

#### API não responde

1. Verifique se a API está habilitada no config
2. Confirme as chaves de API
3. Verifique a conectividade de rede

#### Pagamento recusado

1. Verifique os dados do cartão
2. Confirme se há saldo/limite
3. Verifique se o cartão não está bloqueado

#### PIX não gera

1. Configure a chave PIX no painel admin
2. Verifique se o QR Code está sendo gerado
3. Confirme se a biblioteca qrcode está instalada

### Logs

Os logs são salvos no banco de dados na tabela `payment_notifications`.

## 📞 Suporte

Para suporte técnico:

1. Verifique os logs no painel administrativo
2. Consulte a documentação da API específica
3. Teste em ambiente sandbox primeiro

## 🔄 Atualizações

### Próximas Funcionalidades

- [ ] Suporte a mais gateways (Cielo, Rede, etc.)
- [ ] Pagamento recorrente
- [ ] Split de pagamento
- [ ] Antifraude avançado
- [ ] Relatórios detalhados
- [ ] API REST para integração externa

---

**⚠️ Importante**: Sempre teste em ambiente sandbox antes de usar em produção!

