"""
Sistema de Notas Fiscais e Relatórios de Venda
Gera notas fiscais, cupons fiscais e relatórios de venda
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import streamlit as st
from database import get_conn, get_order_details_full, get_user_by_id, get_product_by_id

class InvoiceGenerator:
    """Gerador de notas fiscais e relatórios"""
    
    def __init__(self):
        self.company_info = {
            "nome": "E-Store LTDA",
            "cnpj": "12.345.678/0001-90",
            "inscricao_estadual": "123.456.789.012",
            "endereco": "Rua das Flores, 123",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep": "01234-567",
            "telefone": "(11) 99999-9999",
            "email": "contato@estore.com"
        }
    
    def generate_invoice(self, order_id: int) -> Dict:
        """Gera nota fiscal para um pedido"""
        try:
            # Buscar dados do pedido
            order_data = get_order_details_full(order_id)
            if not order_data:
                return {"success": False, "error": "Pedido não encontrado"}
            
            order = order_data["order"]
            items = order_data["items"]
            
            # Buscar dados do cliente
            user = get_user_by_id(order["user_id"])
            if not user:
                return {"success": False, "error": "Cliente não encontrado"}
            
            # Gerar número da nota fiscal
            invoice_number = self._generate_invoice_number()
            
            # Calcular impostos (simulado)
            subtotal = float(order["total_amount"])
            tax_rate = 0.18  # 18% de impostos (ICMS + PIS + COFINS)
            tax_amount = subtotal * tax_rate
            total = subtotal + tax_amount
            
            # Estrutura da nota fiscal
            invoice = {
                "invoice_number": invoice_number,
                "invoice_date": datetime.now().strftime("%d/%m/%Y"),
                "invoice_time": datetime.now().strftime("%H:%M:%S"),
                "order_number": order["order_number"],
                "order_id": order_id,
                
                # Dados da empresa
                "company": self.company_info,
                
                # Dados do cliente
                "customer": {
                    "name": f"{user['first_name']} {user['last_name']}",
                    "email": user["email"],
                    "phone": user.get("phone", ""),
                    "address": order.get("shipping_address", ""),
                    "document": "CPF não informado"  # Seria necessário campo no banco
                },
                
                # Itens da nota
                "items": [],
                
                # Totais
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "tax_rate": tax_rate,
                "total": total,
                
                # Informações de pagamento
                "payment_method": order.get("payment_method", ""),
                "payment_status": order.get("payment_status", ""),
                
                # Status
                "status": "EMITIDA",
                "created_at": datetime.now().isoformat()
            }
            
            # Processar itens
            for item in items:
                product = get_product_by_id(item["product_id"])
                if product:
                    invoice["items"].append({
                        "product_id": item["product_id"],
                        "name": product["name"],
                        "description": product.get("description", ""),
                        "sku": product.get("sku", ""),
                        "quantity": item["quantity"],
                        "unit_price": float(item["price"]),
                        "total_price": float(item["price"]) * item["quantity"]
                    })
            
            # Salvar nota fiscal no banco
            self._save_invoice(invoice)
            
            return {
                "success": True,
                "invoice": invoice,
                "message": f"Nota fiscal {invoice_number} gerada com sucesso!"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Erro ao gerar nota fiscal: {str(e)}"}
    
    def _generate_invoice_number(self) -> str:
        """Gera número único da nota fiscal"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"NF{timestamp}"
    
    def _save_invoice(self, invoice: Dict) -> bool:
        """Salva nota fiscal no banco de dados"""
        try:
            conn = get_conn()
            cur = conn.cursor()
            
            # Criar tabela se não existir
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT UNIQUE NOT NULL,
                    order_id INTEGER NOT NULL,
                    customer_name TEXT NOT NULL,
                    customer_email TEXT NOT NULL,
                    subtotal DECIMAL(10,2) NOT NULL,
                    tax_amount DECIMAL(10,2) NOT NULL,
                    total DECIMAL(10,2) NOT NULL,
                    payment_method TEXT,
                    status TEXT DEFAULT 'EMITIDA',
                    invoice_data TEXT NOT NULL,
                    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                )
            """)
            
            # Inserir nota fiscal
            cur.execute("""
                INSERT INTO invoices (
                    invoice_number, order_id, customer_name, customer_email,
                    subtotal, tax_amount, total, payment_method, status, invoice_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice["invoice_number"],
                invoice["order_id"],
                invoice["customer"]["name"],
                invoice["customer"]["email"],
                invoice["subtotal"],
                invoice["tax_amount"],
                invoice["total"],
                invoice["payment_method"],
                invoice["status"],
                json.dumps(invoice, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Erro ao salvar nota fiscal: {e}")
            return False
    
    def get_invoice(self, invoice_number: str) -> Optional[Dict]:
        """Busca nota fiscal por número"""
        try:
            conn = get_conn()
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM invoices WHERE invoice_number = ?", (invoice_number,))
            row = cur.fetchone()
            conn.close()
            
            if row:
                return json.loads(row["invoice_data"])
            return None
            
        except Exception as e:
            print(f"Erro ao buscar nota fiscal: {e}")
            return None
    
    def get_invoices_by_order(self, order_id: int) -> List[Dict]:
        """Busca notas fiscais de um pedido"""
        try:
            conn = get_conn()
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM invoices WHERE order_id = ? ORDER BY created_at DESC", (order_id,))
            rows = cur.fetchall()
            conn.close()
            
            invoices = []
            for row in rows:
                invoices.append(json.loads(row["invoice_data"]))
            
            return invoices
            
        except Exception as e:
            print(f"Erro ao buscar notas fiscais: {e}")
            return []
    
    def generate_sales_report(self, start_date: str = None, end_date: str = None) -> Dict:
        """Gera relatório de vendas"""
        try:
            conn = get_conn()
            cur = conn.cursor()
            
            # Query base
            query = """
                SELECT 
                    o.id,
                    o.order_number,
                    o.total_amount,
                    o.payment_method,
                    o.payment_status,
                    o.created_at,
                    u.first_name,
                    u.last_name,
                    u.email
                FROM orders o
                JOIN users u ON o.user_id = u.id
                WHERE o.status = 'completed'
            """
            
            params = []
            if start_date:
                start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
                query += " AND o.created_at >= ?"
                params.append(start_timestamp)
            
            if end_date:
                end_timestamp = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp()) + 86399
                query += " AND o.created_at <= ?"
                params.append(end_timestamp)
            
            query += " ORDER BY o.created_at DESC"
            
            cur.execute(query, params)
            orders = cur.fetchall()
            
            # Calcular estatísticas
            total_orders = len(orders)
            total_revenue = sum(float(order["total_amount"]) for order in orders)
            
            # Vendas por método de pagamento
            payment_methods = {}
            for order in orders:
                method = order["payment_method"] or "Não informado"
                if method not in payment_methods:
                    payment_methods[method] = {"count": 0, "amount": 0}
                payment_methods[method]["count"] += 1
                payment_methods[method]["amount"] += float(order["total_amount"])
            
            # Vendas por dia
            daily_sales = {}
            for order in orders:
                date = datetime.fromtimestamp(order["created_at"]).strftime("%Y-%m-%d")
                if date not in daily_sales:
                    daily_sales[date] = {"orders": 0, "revenue": 0}
                daily_sales[date]["orders"] += 1
                daily_sales[date]["revenue"] += float(order["total_amount"])
            
            conn.close()
            
            return {
                "success": True,
                "report": {
                    "period": {
                        "start_date": start_date,
                        "end_date": end_date
                    },
                    "summary": {
                        "total_orders": total_orders,
                        "total_revenue": total_revenue,
                        "average_order_value": total_revenue / total_orders if total_orders > 0 else 0
                    },
                    "payment_methods": payment_methods,
                    "daily_sales": daily_sales,
                    "orders": [dict(order) for order in orders],
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Erro ao gerar relatório: {str(e)}"}

def render_invoice_page():
    """Renderiza página de notas fiscais"""
    st.markdown("## 🧾 Sistema de Notas Fiscais")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Gerar Nota", "🔍 Consultar", "📊 Relatórios", "⚙️ Configurações"])
    
    with tab1:
        st.markdown("### 📋 Gerar Nota Fiscal")
        
        # Buscar pedidos para gerar nota
        conn = get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT o.id, o.order_number, o.total_amount, o.created_at, 
                   u.first_name, u.last_name, u.email
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.status = 'completed'
            ORDER BY o.created_at DESC
            LIMIT 50
        """)
        orders = cur.fetchall()
        conn.close()
        
        if orders:
            # Selecionar pedido
            order_options = {
                f"{order['order_number']} - {order['first_name']} {order['last_name']} - R$ {order['total_amount']:,.2f}": order['id']
                for order in orders
            }
            
            selected_order = st.selectbox("Selecione o pedido:", list(order_options.keys()))
            
            if st.button("🧾 Gerar Nota Fiscal", type="primary"):
                order_id = order_options[selected_order]
                
                with st.spinner("Gerando nota fiscal..."):
                    generator = InvoiceGenerator()
                    result = generator.generate_invoice(order_id)
                    
                    if result["success"]:
                        st.success(result["message"])
                        
                        # Mostrar nota fiscal
                        invoice = result["invoice"]
                        
                        st.markdown("### 📄 Nota Fiscal Gerada")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"**Número:** {invoice['invoice_number']}")
                            st.markdown(f"**Data:** {invoice['invoice_date']}")
                            st.markdown(f"**Hora:** {invoice['invoice_time']}")
                            st.markdown(f"**Pedido:** {invoice['order_number']}")
                        
                        with col2:
                            st.markdown(f"**Cliente:** {invoice['customer']['name']}")
                            st.markdown(f"**Email:** {invoice['customer']['email']}")
                            st.markdown(f"**Total:** R$ {invoice['total']:,.2f}")
                            st.markdown(f"**Status:** {invoice['status']}")
                        
                        # Itens da nota
                        st.markdown("### 📦 Itens")
                        for item in invoice["items"]:
                            st.markdown(f"**{item['name']}** - Qtd: {item['quantity']} - R$ {item['total_price']:,.2f}")
                        
                        # Totais
                        st.markdown("### 💰 Totais")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Subtotal", f"R$ {invoice['subtotal']:,.2f}")
                        with col2:
                            st.metric("Impostos", f"R$ {invoice['tax_amount']:,.2f}")
                        with col3:
                            st.metric("Total", f"R$ {invoice['total']:,.2f}")
                        
                        # Botão para baixar
                        if st.button("📥 Baixar Nota Fiscal"):
                            st.info("Funcionalidade de download será implementada")
                    else:
                        st.error(f"❌ {result['error']}")
        else:
            st.info("Nenhum pedido encontrado para gerar nota fiscal")
    
    with tab2:
        st.markdown("### 🔍 Consultar Notas Fiscais")
        
        # Buscar notas fiscais
        conn = get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT invoice_number, order_id, customer_name, total, created_at
            FROM invoices
            ORDER BY created_at DESC
            LIMIT 50
        """)
        invoices = cur.fetchall()
        conn.close()
        
        if invoices:
            for invoice in invoices:
                with st.expander(f"Nota {invoice['invoice_number']} - R$ {invoice['total']:,.2f}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Cliente:** {invoice['customer_name']}")
                        st.markdown(f"**Pedido:** {invoice['order_id']}")
                    with col2:
                        st.markdown(f"**Total:** R$ {invoice['total']:,.2f}")
                        st.markdown(f"**Data:** {datetime.fromtimestamp(invoice['created_at']).strftime('%d/%m/%Y %H:%M')}")
                    
                    if st.button(f"Ver Detalhes", key=f"view_{invoice['invoice_number']}"):
                        generator = InvoiceGenerator()
                        invoice_data = generator.get_invoice(invoice['invoice_number'])
                        if invoice_data:
                            st.json(invoice_data)
        else:
            st.info("Nenhuma nota fiscal encontrada")
    
    with tab3:
        st.markdown("### 📊 Relatórios de Venda")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Data Inicial", value=datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Data Final", value=datetime.now())
        
        if st.button("📈 Gerar Relatório", type="primary"):
            with st.spinner("Gerando relatório..."):
                generator = InvoiceGenerator()
                result = generator.generate_sales_report(
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                
                if result["success"]:
                    report = result["report"]
                    
                    # Resumo
                    st.markdown("### 📊 Resumo do Período")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total de Pedidos", report["summary"]["total_orders"])
                    with col2:
                        st.metric("Receita Total", f"R$ {report['summary']['total_revenue']:,.2f}")
                    with col3:
                        st.metric("Ticket Médio", f"R$ {report['summary']['average_order_value']:,.2f}")
                    
                    # Vendas por método de pagamento
                    st.markdown("### 💳 Vendas por Método de Pagamento")
                    for method, data in report["payment_methods"].items():
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(f"{method} - Pedidos", data["count"])
                        with col2:
                            st.metric(f"{method} - Valor", f"R$ {data['amount']:,.2f}")
                    
                    # Vendas diárias
                    st.markdown("### 📅 Vendas Diárias")
                    daily_data = []
                    for date, data in report["daily_sales"].items():
                        daily_data.append({
                            "Data": datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m"),
                            "Pedidos": data["orders"],
                            "Receita": data["revenue"]
                        })
                    
                    if daily_data:
                        import pandas as pd
                        df = pd.DataFrame(daily_data)
                        st.dataframe(df, use_container_width=True)
                else:
                    st.error(f"❌ {result['error']}")
    
    with tab4:
        st.markdown("### ⚙️ Configurações da Empresa")
        
        st.info("Configurações da empresa para emissão de notas fiscais")
        
        # Mostrar configurações atuais
        generator = InvoiceGenerator()
        company = generator.company_info
        
        st.markdown("**Dados Atuais:**")
        for key, value in company.items():
            st.markdown(f"- **{key.title()}:** {value}")
        
        st.warning("⚠️ Para alterar as configurações, edite o arquivo `invoice_system.py`")

# Função para ser chamada do app principal
def render_invoice_system():
    """Função principal para renderizar o sistema de notas fiscais"""
    render_invoice_page()
