# 📊 Relatório: O que acontece no banco quando você clica em "Comprar"

## 🛒 **Processo de Compra Completo**

Quando você clica em "Comprar" no sistema, uma série de operações são executadas no banco de dados. Aqui está o fluxo completo:

---

## 📋 **1. Dados Salvos no Banco de Dados**

### **Tabela: `orders` (Pedidos)**

```sql
INSERT INTO orders (
    user_id,           -- ID do usuário que fez a compra
    order_number,      -- Número único do pedido (ex: ORD-20241001114930123)
    status,            -- Status do pedido (pending, completed, cancelled)
    total_amount,      -- Valor total da compra
    shipping_address,  -- Endereço de entrega
    billing_address,   -- Endereço de cobrança
    payment_method,    -- Método de pagamento (PIX, Cartão, Boleto)
    payment_status,    -- Status do pagamento (pending, paid, failed)
    created_at,        -- Data/hora da criação
    updated_at         -- Data/hora da última atualização
)
```

### **Tabela: `order_items` (Itens do Pedido)**

```sql
INSERT INTO order_items (
    order_id,          -- ID do pedido
    product_id,        -- ID do produto comprado
    quantity,          -- Quantidade comprada
    price             -- Preço unitário no momento da compra
)
```

### **Tabela: `payment_transactions` (Transações de Pagamento)**

```sql
INSERT INTO payment_transactions (
    order_id,              -- ID do pedido
    transaction_id,        -- ID único da transação (ex: PIX_20241001_123456)
    payment_method,        -- Método de pagamento
    amount,               -- Valor da transação
    status,               -- Status (pending, approved, failed)
    gateway_response,     -- Resposta do gateway de pagamento
    pix_key,             -- Chave PIX (se PIX)
    pix_qr_code,         -- QR Code PIX (se PIX)
    boleto_number,       -- Número do boleto (se boleto)
    boleto_barcode,      -- Código de barras (se boleto)
    boleto_due_date,     -- Data de vencimento (se boleto)
    card_last_four,      -- Últimos 4 dígitos do cartão (se cartão)
    card_brand,          -- Bandeira do cartão (se cartão)
    installments,        -- Número de parcelas (se cartão)
    created_at,          -- Data/hora da transação
    updated_at           -- Data/hora da última atualização
)
```

### **Tabela: `payment_notifications` (Notificações)**

```sql
INSERT INTO payment_notifications (
    transaction_id,        -- ID da transação
    notification_type,     -- Tipo (payment_approved, payment_failed)
    status,               -- Status da notificação
    message,              -- Mensagem da notificação
    processed_at,         -- Data/hora do processamento
    created_at            -- Data/hora da criação
)
```

---

## 🔄 **2. Operações Executadas Durante a Compra**

### **Passo 1: Validação do Carrinho**

- Verifica se há itens no carrinho
- Calcula o total da compra
- Valida estoque dos produtos

### **Passo 2: Criação do Pedido**

- Gera número único do pedido
- Salva dados do pedido na tabela `orders`
- Cria itens do pedido na tabela `order_items`
- Atualiza estoque dos produtos (diminui quantidade)

### **Passo 3: Processamento do Pagamento**

- Processa pagamento conforme método escolhido
- Salva transação na tabela `payment_transactions`
- Cria notificação na tabela `payment_notifications`

### **Passo 4: Finalização**

- Limpa carrinho do usuário
- Atualiza status do pedido
- Redireciona para página de confirmação

---

## 📊 **3. Exemplo de Dados Salvos**

### **Pedido Exemplo:**

```json
{
  "order_id": 123,
  "order_number": "ORD-20241001114930123",
  "user_id": 45,
  "status": "completed",
  "total_amount": 299.9,
  "shipping_address": "Rua das Flores, 123 - São Paulo/SP",
  "payment_method": "PIX",
  "payment_status": "paid",
  "created_at": 1727771370
}
```

### **Itens do Pedido:**

```json
[
  {
    "order_id": 123,
    "product_id": 15,
    "quantity": 2,
    "price": 149.95
  }
]
```

### **Transação de Pagamento:**

```json
{
  "order_id": 123,
  "transaction_id": "PIX_20241001_123456",
  "payment_method": "PIX",
  "amount": 299.9,
  "status": "approved",
  "pix_key": "pix_key_abc123",
  "pix_qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "created_at": 1727771370
}
```

---

## 🧾 **4. Sistema de Notas Fiscais (NOVO!)**

### **Tabela: `invoices` (Notas Fiscais)**

```sql
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,    -- Número da nota fiscal
    order_id INTEGER NOT NULL,              -- ID do pedido
    customer_name TEXT NOT NULL,            -- Nome do cliente
    customer_email TEXT NOT NULL,           -- Email do cliente
    subtotal DECIMAL(10,2) NOT NULL,        -- Subtotal
    tax_amount DECIMAL(10,2) NOT NULL,      -- Valor dos impostos
    total DECIMAL(10,2) NOT NULL,           -- Total com impostos
    payment_method TEXT,                    -- Método de pagamento
    status TEXT DEFAULT 'EMITIDA',          -- Status da nota
    invoice_data TEXT NOT NULL,             -- Dados completos da nota (JSON)
    created_at INTEGER NOT NULL             -- Data/hora de criação
)
```

### **Dados da Nota Fiscal:**

```json
{
  "invoice_number": "NF20241001114930",
  "invoice_date": "01/10/2024",
  "invoice_time": "11:49:30",
  "order_number": "ORD-20241001114930123",
  "company": {
    "nome": "E-Store LTDA",
    "cnpj": "12.345.678/0001-90",
    "endereco": "Rua das Flores, 123"
  },
  "customer": {
    "name": "João Silva",
    "email": "joao@email.com",
    "address": "Rua das Flores, 123 - São Paulo/SP"
  },
  "items": [
    {
      "name": "Produto Exemplo",
      "quantity": 2,
      "unit_price": 149.95,
      "total_price": 299.9
    }
  ],
  "subtotal": 299.9,
  "tax_amount": 53.98,
  "total": 353.88,
  "status": "EMITIDA"
}
```

---

## 📈 **5. Relatórios Disponíveis**

### **Relatório de Vendas:**

- Total de pedidos por período
- Receita total
- Ticket médio
- Vendas por método de pagamento
- Vendas diárias

### **Relatório de Notas Fiscais:**

- Notas emitidas por período
- Total de impostos recolhidos
- Clientes que mais compram
- Produtos mais vendidos

---

## 🎯 **6. Como Acessar os Dados**

### **No Sistema Streamlit:**

1. **Dashboard Admin** → **Notas Fiscais**
2. **Dashboard Admin** → **Relatórios de Vendas**
3. **Dashboard Admin** → **Pedidos**

### **No Banco de Dados:**

```sql
-- Ver todos os pedidos
SELECT * FROM orders ORDER BY created_at DESC;

-- Ver transações de pagamento
SELECT * FROM payment_transactions ORDER BY created_at DESC;

-- Ver notas fiscais
SELECT * FROM invoices ORDER BY created_at DESC;

-- Relatório de vendas
SELECT
    DATE(datetime(created_at, 'unixepoch')) as data,
    COUNT(*) as pedidos,
    SUM(total_amount) as receita
FROM orders
WHERE status = 'completed'
GROUP BY DATE(datetime(created_at, 'unixepoch'))
ORDER BY data DESC;
```

---

## ✅ **Resumo: O que é Gerado**

Quando você clica em "Comprar", o sistema gera:

1. **📋 Pedido** - Registro completo da compra
2. **💳 Transação** - Dados do pagamento processado
3. **📦 Itens** - Detalhes dos produtos comprados
4. **🔔 Notificação** - Confirmação do pagamento
5. **🧾 Nota Fiscal** - Documento fiscal (se solicitado)
6. **📊 Relatórios** - Dados para análise de vendas

**Tudo fica salvo no banco de dados SQLite (`ecommerce.db`) e pode ser consultado a qualquer momento!**
