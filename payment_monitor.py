"""
Sistema de Monitoramento de Pagamentos
Verifica status de pagamentos PIX, boleto e cartão
"""

import streamlit as st
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List
from database import get_payment_transaction, update_payment_status, create_payment_notification


class PaymentMonitor:
    """Monitor de status de pagamentos"""
    
    def __init__(self):
        self.check_interval = 30  # segundos
    
    def check_pix_payment(self, transaction_id: str) -> Dict:
        """Verifica status do pagamento PIX"""
        # Simular verificação de PIX
        import random
        
        # 70% de chance de pagamento aprovado após 2 minutos
        if random.random() < 0.7:
            return {
                "status": "approved",
                "message": "Pagamento PIX confirmado",
                "confirmed_at": datetime.now().timestamp()
            }
        else:
            return {
                "status": "pending",
                "message": "Aguardando pagamento PIX"
            }
    
    def check_boleto_payment(self, transaction_id: str) -> Dict:
        """Verifica status do pagamento via boleto"""
        # Simular verificação de boleto
        import random
        
        # 60% de chance de pagamento aprovado após 1 dia
        if random.random() < 0.6:
            return {
                "status": "approved",
                "message": "Boleto pago confirmado",
                "confirmed_at": datetime.now().timestamp()
            }
        else:
            return {
                "status": "pending",
                "message": "Aguardando pagamento do boleto"
            }
    
    def check_credit_card_payment(self, transaction_id: str) -> Dict:
        """Verifica status do pagamento via cartão"""
        # Cartão de crédito é processado imediatamente
        transaction = get_payment_transaction(transaction_id)
        
        if transaction and transaction['status'] == 'approved':
            return {
                "status": "approved",
                "message": "Pagamento com cartão aprovado",
                "confirmed_at": transaction['created_at']
            }
        else:
            return {
                "status": "failed",
                "message": "Pagamento com cartão recusado"
            }
    
    def check_payment_status(self, transaction_id: str) -> Dict:
        """Verifica status de qualquer tipo de pagamento"""
        transaction = get_payment_transaction(transaction_id)
        
        if not transaction:
            return {"status": "not_found", "message": "Transação não encontrada"}
        
        # Se já foi processado, retornar status atual
        if transaction['status'] in ['approved', 'failed', 'cancelled']:
            return {
                "status": transaction['status'],
                "message": f"Status: {transaction['status']}",
                "confirmed_at": transaction['updated_at']
            }
        
        # Verificar baseado no método de pagamento
        payment_method = transaction['payment_method']
        
        if payment_method == 'PIX':
            return self.check_pix_payment(transaction_id)
        elif payment_method == 'Boleto Bancário':
            return self.check_boleto_payment(transaction_id)
        elif payment_method == 'Cartão de Crédito':
            return self.check_credit_card_payment(transaction_id)
        else:
            return {"status": "unknown", "message": "Método de pagamento não reconhecido"}
    
    def update_payment_if_approved(self, transaction_id: str) -> bool:
        """Atualiza status do pagamento se foi aprovado"""
        status_check = self.check_payment_status(transaction_id)
        
        if status_check['status'] == 'approved':
            # Atualizar no banco de dados
            success = update_payment_status(
                transaction_id, 
                'approved', 
                json.dumps(status_check)
            )
            
            if success:
                # Criar notificação
                create_payment_notification(
                    transaction_id,
                    'payment_approved',
                    'success',
                    status_check['message']
                )
                return True
        
        return False
    
    def get_pending_payments(self) -> List[Dict]:
        """Retorna lista de pagamentos pendentes"""
        from database import get_conn
        
        conn = get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT pt.*, o.order_number, u.first_name, u.last_name
            FROM payment_transactions pt
            JOIN orders o ON pt.order_id = o.id
            JOIN users u ON o.user_id = u.id
            WHERE pt.status = 'pending'
            ORDER BY pt.created_at ASC
        """)
        
        pending_payments = cur.fetchall()
        conn.close()
        
        return [dict(payment) for payment in pending_payments]
    
    def process_pending_payments(self) -> Dict:
        """Processa todos os pagamentos pendentes"""
        pending_payments = self.get_pending_payments()
        
        results = {
            'total_checked': len(pending_payments),
            'approved': 0,
            'still_pending': 0,
            'failed': 0
        }
        
        for payment in pending_payments:
            transaction_id = payment['transaction_id']
            
            # Verificar se foi aprovado
            if self.update_payment_if_approved(transaction_id):
                results['approved'] += 1
            else:
                # Verificar se falhou (ex: PIX expirado)
                if self._is_payment_expired(payment):
                    update_payment_status(transaction_id, 'failed', 'Pagamento expirado')
                    results['failed'] += 1
                else:
                    results['still_pending'] += 1
        
        return results
    
    def _is_payment_expired(self, payment: Dict) -> bool:
        """Verifica se o pagamento expirou"""
        payment_method = payment['payment_method']
        created_at = payment['created_at']
        
        # PIX expira em 30 minutos
        if payment_method == 'PIX':
            expiry_time = created_at + (30 * 60)  # 30 minutos
            return time.time() > expiry_time
        
        # Boleto expira em 3 dias
        elif payment_method == 'Boleto Bancário':
            expiry_time = created_at + (3 * 24 * 60 * 60)  # 3 dias
            return time.time() > expiry_time
        
        # Cartão não expira (é processado imediatamente)
        return False


def render_payment_monitor_page():
    """Renderiza página de monitoramento de pagamentos"""
    st.markdown("## 🔍 Monitor de Pagamentos")
    
    monitor = PaymentMonitor()
    
    # Botões de ação
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Verificar Pagamentos Pendentes", use_container_width=True):
            with st.spinner("Verificando pagamentos..."):
                results = monitor.process_pending_payments()
                
                st.success(f"""
                **📊 Resultado da Verificação:**
                - ✅ **Aprovados:** {results['approved']}
                - ⏳ **Ainda Pendentes:** {results['still_pending']}
                - ❌ **Falharam:** {results['failed']}
                - 📋 **Total Verificados:** {results['total_checked']}
                """)
    
    with col2:
        if st.button("📋 Listar Pendentes", use_container_width=True):
            pending_payments = monitor.get_pending_payments()
            
            if pending_payments:
                st.markdown("### ⏳ Pagamentos Pendentes")
                
                for payment in pending_payments:
                    with st.expander(f"💳 {payment['transaction_id']} - {payment['payment_method']} - R$ {payment['amount']:,.2f}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"**👤 Cliente:** {payment['first_name']} {payment['last_name']}")
                            st.markdown(f"**📋 Pedido:** {payment['order_number']}")
                            st.markdown(f"**💰 Valor:** R$ {payment['amount']:,.2f}")
                            st.markdown(f"**📅 Criado:** {datetime.fromtimestamp(payment['created_at']).strftime('%d/%m/%Y %H:%M')}")
                        
                        with col2:
                            # Verificar status individual
                            if st.button(f"🔍 Verificar", key=f"check_{payment['transaction_id']}"):
                                status = monitor.check_payment_status(payment['transaction_id'])
                                
                                if status['status'] == 'approved':
                                    st.success(f"✅ {status['message']}")
                                    # Atualizar automaticamente
                                    monitor.update_payment_if_approved(payment['transaction_id'])
                                    st.rerun()
                                else:
                                    st.info(f"⏳ {status['message']}")
            else:
                st.info("🎉 Nenhum pagamento pendente!")
    
    with col3:
        if st.button("📊 Estatísticas", use_container_width=True):
            # Mostrar estatísticas
            from database import get_conn
            
            conn = get_conn()
            cur = conn.cursor()
            
            # Estatísticas gerais
            cur.execute("SELECT COUNT(*) FROM payment_transactions")
            total_transactions = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM payment_transactions WHERE status = 'approved'")
            approved_transactions = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM payment_transactions WHERE status = 'pending'")
            pending_transactions = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM payment_transactions WHERE status = 'failed'")
            failed_transactions = cur.fetchone()[0]
            
            # Receita total
            cur.execute("SELECT SUM(amount) FROM payment_transactions WHERE status = 'approved'")
            total_revenue = cur.fetchone()[0] or 0
            
            conn.close()
            
            # Exibir estatísticas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de Transações", total_transactions)
            with col2:
                st.metric("Pagamentos Aprovados", approved_transactions)
            with col3:
                st.metric("Pagamentos Pendentes", pending_transactions)
            with col4:
                st.metric("Receita Total", f"R$ {total_revenue:,.2f}")
            
            # Taxa de aprovação
            if total_transactions > 0:
                approval_rate = (approved_transactions / total_transactions) * 100
                st.metric("Taxa de Aprovação", f"{approval_rate:.1f}%")
    
    # Monitoramento automático
    st.markdown("---")
    st.markdown("### 🤖 Monitoramento Automático")
    
    if st.checkbox("🔄 Ativar verificação automática"):
        st.info("💡 O sistema verificará pagamentos pendentes automaticamente a cada 30 segundos.")
        
        # Simular verificação automática
        if st.button("▶️ Iniciar Monitoramento"):
            placeholder = st.empty()
            
            for i in range(5):  # Simular 5 verificações
                with placeholder.container():
                    st.write(f"🔄 Verificação {i+1}/5...")
                    time.sleep(1)
                    
                    # Simular verificação
                    results = monitor.process_pending_payments()
                    st.write(f"✅ {results['approved']} aprovados, ⏳ {results['still_pending']} pendentes")
            
            st.success("✅ Monitoramento concluído!")
    
    # Histórico de verificações
    st.markdown("### 📋 Histórico de Verificações")
    
    # Simular histórico
    verification_history = [
        {"time": "16:30:15", "approved": 2, "pending": 1, "failed": 0},
        {"time": "16:29:45", "approved": 1, "pending": 2, "failed": 0},
        {"time": "16:29:15", "approved": 0, "pending": 3, "failed": 0},
    ]
    
    for entry in verification_history:
        st.markdown(f"🕐 **{entry['time']}** - ✅ {entry['approved']} aprovados, ⏳ {entry['pending']} pendentes, ❌ {entry['failed']} falharam")


def get_payment_monitor() -> PaymentMonitor:
    """Retorna instância do monitor de pagamentos"""
    return PaymentMonitor()

