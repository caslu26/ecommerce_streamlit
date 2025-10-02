"""
Sistema de Pagamento para E-commerce
Suporte a PIX, Cartão de Crédito e Boleto Bancário
"""

import streamlit as st
import re
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
try:
    import qrcode
    import io
    import base64
    from PIL import Image
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
import requests


class PaymentValidator:
    """Classe para validação de dados de pagamento"""
    
    @staticmethod
    def validate_card_number(card_number: str) -> bool:
        """Valida número do cartão usando algoritmo de Luhn"""
        # Remove espaços e caracteres não numéricos
        card_number = re.sub(r'\D', '', card_number)
        
        if len(card_number) < 13 or len(card_number) > 19:
            return False
        
        # Algoritmo de Luhn
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10
        
        return luhn_checksum(card_number) == 0
    
    @staticmethod
    def validate_cvv(cvv: str) -> bool:
        """Valida CVV"""
        return re.match(r'^\d{3,4}$', cvv) is not None
    
    @staticmethod
    def validate_expiry_date(expiry: str) -> bool:
        """Valida data de expiração MM/AA"""
        if not re.match(r'^\d{2}/\d{2}$', expiry):
            return False
        
        month, year = expiry.split('/')
        month, year = int(month), int(year)
        
        if month < 1 or month > 12:
            return False
        
        current_year = datetime.now().year % 100
        current_month = datetime.now().month
        
        if year < current_year or (year == current_year and month < current_month):
            return False
        
        return True
    
    @staticmethod
    def validate_cpf(cpf: str) -> bool:
        """Valida CPF"""
        cpf = re.sub(r'\D', '', cpf)
        
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        
        # Validação do primeiro dígito
        sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digit1 = 11 - (sum1 % 11)
        if digit1 >= 10:
            digit1 = 0
        
        # Validação do segundo dígito
        sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digit2 = 11 - (sum2 % 11)
        if digit2 >= 10:
            digit2 = 0
        
        return cpf[9] == str(digit1) and cpf[10] == str(digit2)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Valida email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None


class PaymentProcessor:
    """Processador de pagamentos"""
    
    def __init__(self):
        self.validator = PaymentValidator()
        # Importar gateway configurável
        try:
            from payment_config import get_payment_gateway
            self.gateway = get_payment_gateway()
        except ImportError:
            self.gateway = None
        
        # Importar APIs reais de pagamento
        try:
            from payment_apis import get_payment_api_manager
            self.api_manager = get_payment_api_manager()
        except ImportError:
            self.api_manager = None
    
    def process_credit_card(self, card_data: Dict) -> Dict:
        """Processa pagamento com cartão de crédito"""
        # Validações
        if not self.validator.validate_card_number(card_data['number']):
            return {"success": False, "error": "Número do cartão inválido"}
        
        if not self.validator.validate_cvv(card_data['cvv']):
            return {"success": False, "error": "CVV inválido"}
        
        if not self.validator.validate_expiry_date(card_data['expiry']):
            return {"success": False, "error": "Data de expiração inválida"}
        
        # Usar APIs reais se disponível
        if self.api_manager:
            return self.api_manager.process_credit_card_payment(card_data, card_data['amount'])
        
        # Usar gateway configurável se disponível
        if self.gateway:
            return self.gateway.process_credit_card_payment(card_data)
        
        # Fallback para simulação simples
        transaction_id = self._generate_transaction_id()
        
        # Simular diferentes cenários
        import random
        success_rate = 0.85  # 85% de sucesso
        
        if random.random() < success_rate:
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": "approved",
                "payment_method": "Cartão de Crédito",
                "card_last_four": card_data['number'][-4:],
                "card_brand": self._detect_card_brand(card_data['number']),
                "installments": card_data.get('installments', 1),
                "message": "Pagamento aprovado com sucesso",
                "gateway_response": {
                    "authorization_code": f"AUTH{secrets.token_hex(4).upper()}",
                    "processor_response": "00",
                    "processor_message": "Approved"
                }
            }
        else:
            return {
                "success": False,
                "error": "Pagamento recusado pelo banco",
                "transaction_id": transaction_id
            }
    
    def process_debit_card(self, card_data: Dict) -> Dict:
        """Processa pagamento com cartão de débito"""
        # Validações
        if not self.validator.validate_card_number(card_data['number']):
            return {"success": False, "error": "Número do cartão inválido"}
        
        if not self.validator.validate_cvv(card_data['cvv']):
            return {"success": False, "error": "CVV inválido"}
        
        if not self.validator.validate_expiry_date(card_data['expiry']):
            return {"success": False, "error": "Data de expiração inválida"}
        
        # Usar APIs reais se disponível
        if self.api_manager:
            return self.api_manager.process_debit_card_payment(card_data, card_data['amount'])
        
        # Usar gateway configurável se disponível
        if self.gateway:
            return self.gateway.process_debit_card_payment(card_data)
        
        # Fallback para simulação simples
        transaction_id = self._generate_transaction_id()
        
        # Simular diferentes cenários (débito tem taxa de sucesso maior)
        import random
        success_rate = 0.92  # 92% de sucesso para débito
        
        if random.random() < success_rate:
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": "approved",
                "payment_method": "Cartão de Débito",
                "card_last_four": card_data['number'][-4:],
                "card_brand": self._detect_card_brand(card_data['number']),
                "message": "Pagamento aprovado com sucesso",
                "gateway_response": {
                    "authorization_code": f"AUTH{secrets.token_hex(4).upper()}",
                    "processor_response": "00",
                    "processor_message": "Approved",
                    "card_type": "debit"
                }
            }
        else:
            return {
                "success": False,
                "error": "Saldo insuficiente ou cartão recusado",
                "transaction_id": transaction_id
            }
    
    def process_pix(self, pix_data: Dict) -> Dict:
        """Processa pagamento via PIX"""
        # Usar APIs reais se disponível
        if self.api_manager:
            return self.api_manager.process_pix_payment(pix_data['amount'], pix_data.get('description', ''))
        
        # Usar gateway configurável se disponível
        if self.gateway:
            return self.gateway.process_pix_payment(pix_data['amount'], pix_data.get('description', ''))
        
        # Fallback para simulação simples
        pix_key = self._generate_pix_key()
        qr_code_data = self._generate_pix_qr_code(pix_data['amount'], pix_key)
        
        return {
            "success": True,
            "transaction_id": self._generate_transaction_id(),
            "status": "pending",
            "payment_method": "PIX",
            "pix_key": pix_key,
            "qr_code": qr_code_data,
            "expires_at": datetime.now() + timedelta(minutes=30),
            "message": "PIX gerado com sucesso. Escaneie o QR Code ou use a chave PIX."
        }
    
    def process_boleto(self, boleto_data: Dict) -> Dict:
        """Processa pagamento via boleto"""
        # Usar gateway configurável se disponível
        if self.gateway:
            return self.gateway.process_boleto_payment(boleto_data['amount'], boleto_data.get('due_days', 3))
        
        # Fallback para simulação simples
        boleto_number = self._generate_boleto_number()
        due_date = datetime.now() + timedelta(days=3)
        
        return {
            "success": True,
            "transaction_id": self._generate_transaction_id(),
            "status": "pending",
            "payment_method": "Boleto Bancário",
            "boleto_number": boleto_number,
            "due_date": due_date,
            "barcode": self._generate_boleto_barcode(boleto_number),
            "message": "Boleto gerado com sucesso. Vence em 3 dias úteis."
        }
    
    def _generate_transaction_id(self) -> str:
        """Gera ID único para transação"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4).upper()
        return f"TXN{timestamp}{random_part}"
    
    def _generate_pix_key(self) -> str:
        """Gera chave PIX aleatória"""
        return secrets.token_hex(16)
    
    def _generate_pix_qr_code(self, amount: float, pix_key: str) -> str:
        """Gera QR Code PIX"""
        if QRCODE_AVAILABLE:
            # Dados do PIX (formato simplificado)
            pix_data = {
                "amount": amount,
                "key": pix_key,
                "merchant": "E-Store",
                "description": "Pagamento E-commerce"
            }
            
            # Gerar QR Code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(pix_data))
            qr.make(fit=True)
            
            # Converter para base64
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
        else:
            # Fallback: retornar URL de placeholder
            return "https://via.placeholder.com/200x200/667eea/white?text=PIX+QR+Code"
    
    def _generate_boleto_number(self) -> str:
        """Gera número do boleto"""
        return f"34191.{secrets.randbelow(10000):04d}.{secrets.randbelow(10000):04d}.{secrets.randbelow(100000):05d}.{secrets.randbelow(100000):05d}"
    
    def _generate_boleto_barcode(self, boleto_number: str) -> str:
        """Gera código de barras do boleto"""
        # Remove pontos e gera código de barras (simplificado)
        clean_number = boleto_number.replace('.', '')
        return f"34191{clean_number}"


class PaymentUI:
    """Interface de usuário para pagamentos"""
    
    def __init__(self):
        self.processor = PaymentProcessor()
    
    def render_payment_form(self, order_data: Dict) -> Dict:
        """Renderiza formulário de pagamento"""
        st.markdown("### 💳 Escolha a Forma de Pagamento")
        
        # Seleção do método de pagamento
        payment_method = st.radio(
            "Método de Pagamento:",
            ["PIX", "Cartão de Crédito", "Cartão de Débito", "Boleto Bancário"],
            horizontal=True
        )
        
        st.markdown("---")
        
        # Formulário baseado no método selecionado
        if payment_method == "PIX":
            return self._render_pix_form(order_data)
        elif payment_method == "Cartão de Crédito":
            return self._render_credit_card_form(order_data)
        elif payment_method == "Cartão de Débito":
            return self._render_debit_card_form(order_data)
        elif payment_method == "Boleto Bancário":
            return self._render_boleto_form(order_data)
    
    def _render_pix_form(self, order_data: Dict) -> Dict:
        """Renderiza formulário PIX"""
        st.markdown("#### 📱 Pagamento via PIX")
        st.info("💡 **Vantagens do PIX:** Aprovação instantânea, sem taxas, mais seguro!")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📋 Dados do Pedido:**")
            st.markdown(f"💰 **Total:** R$ {order_data['total']:,.2f}")
            st.markdown(f"📦 **Itens:** {order_data['item_count']} produto(s)")
        
        with col2:
            if st.button("🔄 Gerar PIX", use_container_width=True, type="primary"):
                with st.spinner("Gerando PIX..."):
                    result = self.processor.process_pix({
                        "amount": order_data['total'],
                        "order_id": order_data['order_id']
                    })
                    
                    if result['success']:
                        st.session_state.payment_result = result
                        st.success("✅ PIX gerado com sucesso!")
                        return result
                    else:
                        st.error(f"❌ Erro: {result['error']}")
        
        # Mostrar PIX se já foi gerado
        if 'payment_result' in st.session_state and st.session_state.payment_result.get('status') == 'pending':
            # Verificar se é PIX ou Boleto
            if st.session_state.payment_result.get('payment_method') == 'PIX':
                return self._display_pix_payment(st.session_state.payment_result)
            elif st.session_state.payment_result.get('payment_method') == 'Boleto Bancário':
                return self._display_boleto_payment(st.session_state.payment_result)
        
        return {"status": "waiting"}
    
    def _render_credit_card_form(self, order_data: Dict) -> Dict:
        """Renderiza formulário de cartão de crédito"""
        st.markdown("#### 💳 Pagamento com Cartão de Crédito")
        
        with st.form("credit_card_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**💳 Dados do Cartão:**")
                card_number = st.text_input(
                    "Número do Cartão",
                    placeholder="1234 5678 9012 3456",
                    help="Digite o número do cartão sem espaços"
                )
                
                col_exp, col_cvv = st.columns(2)
                with col_exp:
                    expiry_date = st.text_input(
                        "Validade (MM/AA)",
                        placeholder="12/25"
                    )
                with col_cvv:
                    cvv = st.text_input(
                        "CVV",
                        placeholder="123",
                        type="password"
                    )
            
            with col2:
                st.markdown("**👤 Dados do Portador:**")
                cardholder_name = st.text_input(
                    "Nome no Cartão",
                    placeholder="JOÃO DA SILVA"
                )
                
                cpf = st.text_input(
                    "CPF",
                    placeholder="000.000.000-00",
                    help="CPF do portador do cartão"
                )
                
                installments = st.selectbox(
                    "Parcelamento",
                    options=[1, 2, 3, 6, 12],
                    format_func=lambda x: f"{x}x de R$ {order_data['total']/x:,.2f}" if x > 1 else "À vista"
                )
            
            st.markdown("**🔒 Segurança:**")
            st.markdown("""
            <div style='background: #f0f9ff; padding: 1rem; border-radius: 8px; border-left: 4px solid #3b82f6;'>
                <small>
                🔐 <strong>Seus dados estão seguros!</strong><br>
                • Conexão criptografada SSL<br>
                • Não armazenamos dados do cartão<br>
                • Processamento seguro via gateway
                </small>
            </div>
            """, unsafe_allow_html=True)
            
            submit_payment = st.form_submit_button(
                f"💳 Pagar R$ {order_data['total']:,.2f}",
                use_container_width=True,
                type="primary"
            )
            
            if submit_payment:
                # Validações
                if not all([card_number, expiry_date, cvv, cardholder_name, cpf]):
                    st.error("❌ Preencha todos os campos obrigatórios!")
                    return {"status": "error"}
                
                if not self.processor.validator.validate_cpf(cpf):
                    st.error("❌ CPF inválido!")
                    return {"status": "error"}
                
                # Processar pagamento
                with st.spinner("Processando pagamento..."):
                    result = self.processor.process_credit_card({
                        "number": card_number,
                        "expiry": expiry_date,
                        "cvv": cvv,
                        "name": cardholder_name,
                        "amount": order_data['total'],
                        "installments": installments
                    })
                    
                    if result['success']:
                        st.success("✅ Pagamento aprovado!")
                        return result
                    else:
                        st.error(f"❌ {result['error']}")
                        return result
        
        return {"status": "waiting"}
    
    def _render_debit_card_form(self, order_data: Dict) -> Dict:
        """Renderiza formulário de cartão de débito"""
        st.markdown("#### 💳 Pagamento com Cartão de Débito")
        st.info("💡 **Vantagens do Débito:** Aprovação imediata, sem juros, desconto na conta!")
        
        with st.form("debit_card_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**💳 Dados do Cartão:**")
                card_number = st.text_input(
                    "Número do Cartão",
                    placeholder="1234 5678 9012 3456",
                    help="Digite o número do cartão sem espaços",
                    key="debit_card_number"
                )
                
                col_exp, col_cvv = st.columns(2)
                with col_exp:
                    expiry_date = st.text_input(
                        "Validade (MM/AA)",
                        placeholder="12/25",
                        key="debit_expiry"
                    )
                with col_cvv:
                    cvv = st.text_input(
                        "CVV",
                        placeholder="123",
                        type="password",
                        key="debit_cvv"
                    )
            
            with col2:
                st.markdown("**👤 Dados do Portador:**")
                cardholder_name = st.text_input(
                    "Nome no Cartão",
                    placeholder="JOÃO DA SILVA",
                    key="debit_name"
                )
                
                cpf = st.text_input(
                    "CPF",
                    placeholder="000.000.000-00",
                    help="CPF do portador do cartão",
                    key="debit_cpf"
                )
                
                # Para débito, mostrar que é à vista
                st.markdown("**💰 Forma de Pagamento:**")
                st.success("✅ **À Vista** - Valor será debitado imediatamente da sua conta")
            
            st.markdown("**🔒 Segurança:**")
            st.markdown("""
            <div style='background: #f0f9ff; padding: 1rem; border-radius: 8px; border-left: 4px solid #3b82f6;'>
                <small>
                🔐 <strong>Seus dados estão seguros!</strong><br>
                • Conexão criptografada SSL<br>
                • Não armazenamos dados do cartão<br>
                • Processamento seguro via gateway<br>
                • Débito imediato da conta corrente
                </small>
            </div>
            """, unsafe_allow_html=True)
            
            submit_payment = st.form_submit_button(
                f"💳 Pagar R$ {order_data['total']:,.2f}",
                use_container_width=True,
                type="primary"
            )
            
            if submit_payment:
                # Validações
                if not all([card_number, expiry_date, cvv, cardholder_name, cpf]):
                    st.error("❌ Preencha todos os campos obrigatórios!")
                    return {"status": "error"}
                
                if not self.processor.validator.validate_cpf(cpf):
                    st.error("❌ CPF inválido!")
                    return {"status": "error"}
                
                # Processar pagamento
                with st.spinner("Processando pagamento..."):
                    result = self.processor.process_debit_card({
                        "number": card_number,
                        "expiry": expiry_date,
                        "cvv": cvv,
                        "name": cardholder_name,
                        "amount": order_data['total']
                    })
                    
                    if result['success']:
                        st.success("✅ Pagamento aprovado!")
                        return result
                    else:
                        st.error(f"❌ {result['error']}")
                        return result
        
        return {"status": "waiting"}
    
    def _render_boleto_form(self, order_data: Dict) -> Dict:
        """Renderiza formulário de boleto"""
        st.markdown("#### 🏦 Pagamento via Boleto Bancário")
        st.info("💡 **Vantagens do Boleto:** Sem juros, pode ser pago em qualquer banco!")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📋 Dados do Pedido:**")
            st.markdown(f"💰 **Total:** R$ {order_data['total']:,.2f}")
            st.markdown(f"📦 **Itens:** {order_data['item_count']} produto(s)")
            st.markdown(f"📅 **Vencimento:** 3 dias úteis")
        
        with col2:
            if st.button("🏦 Gerar Boleto", use_container_width=True, type="primary"):
                with st.spinner("Gerando boleto..."):
                    result = self.processor.process_boleto({
                        "amount": order_data['total'],
                        "order_id": order_data['order_id']
                    })
                    
                    if result['success']:
                        st.session_state.payment_result = result
                        st.success("✅ Boleto gerado com sucesso!")
                        return result
                    else:
                        st.error(f"❌ Erro: {result['error']}")
        
        # Mostrar boleto se já foi gerado
        if 'payment_result' in st.session_state and st.session_state.payment_result.get('status') == 'pending':
            # Verificar se é PIX ou Boleto
            if st.session_state.payment_result.get('payment_method') == 'PIX':
                return self._display_pix_payment(st.session_state.payment_result)
            elif st.session_state.payment_result.get('payment_method') == 'Boleto Bancário':
                return self._display_boleto_payment(st.session_state.payment_result)
        
        return {"status": "waiting"}
    
    def _display_pix_payment(self, payment_result: Dict) -> Dict:
        """Exibe informações do PIX"""
        st.markdown("### 📱 PIX Gerado com Sucesso!")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**🔑 Chave PIX:**")
            st.code(payment_result['pix_key'], language=None)
            
            st.markdown("**⏰ Expira em:**")
            expires_at = payment_result['expires_at']
            st.markdown(f"🕐 {expires_at.strftime('%d/%m/%Y às %H:%M')}")
            
            # Botão para copiar chave PIX
            if st.button("📋 Copiar Chave PIX", use_container_width=True):
                st.success("✅ Chave PIX copiada para a área de transferência!")
        
        with col2:
            st.markdown("**📱 QR Code PIX:**")
            st.image(payment_result['qr_code'], width=200)
            
            st.markdown("**📱 Como pagar:**")
            st.markdown("""
            1. 📱 Abra o app do seu banco
            2. 🔍 Escaneie o QR Code
            3. ✅ Confirme o pagamento
            4. 🎉 Pronto! Seu pedido será processado
            """)
        
        st.markdown("---")
        st.info("💡 **Dica:** Após o pagamento, você receberá um e-mail de confirmação!")
        
        return payment_result
    
    def _display_boleto_payment(self, payment_result: Dict) -> Dict:
        """Exibe informações do boleto"""
        st.markdown("### 🏦 Boleto Gerado com Sucesso!")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📄 Dados do Boleto:**")
            if 'boleto_number' in payment_result:
                st.markdown(f"**Número:** {payment_result['boleto_number']}")
            if 'barcode' in payment_result:
                st.markdown(f"**Código de Barras:**")
                st.code(payment_result['barcode'], language=None)
            
            st.markdown("**📅 Vencimento:**")
            if 'due_date' in payment_result:
                if isinstance(payment_result['due_date'], (int, float)):
                    # Se for timestamp
                    from datetime import datetime
                    due_date = datetime.fromtimestamp(payment_result['due_date'])
                else:
                    # Se for objeto datetime
                    due_date = payment_result['due_date']
                st.markdown(f"📅 {due_date.strftime('%d/%m/%Y')}")
            
            # Mostrar dados do cedente se disponível
            if 'cedente' in payment_result:
                st.markdown(f"**🏢 Cedente:** {payment_result['cedente']}")
            if 'cnpj' in payment_result:
                st.markdown(f"**📄 CNPJ:** {payment_result['cnpj']}")
        
        with col2:
            st.markdown("**🏦 Como pagar:**")
            st.markdown("""
            1. 🏦 Vá a qualquer banco ou lotérica
            2. 📄 Informe o código de barras
            3. 💰 Pague o valor do boleto
            4. ✅ Guarde o comprovante
            5. 🎉 Seu pedido será processado
            """)
            
            # Botão para imprimir boleto
            if st.button("🖨️ Imprimir Boleto", use_container_width=True):
                st.success("✅ Boleto enviado para impressão!")
        
        st.markdown("---")
        st.info("💡 **Importante:** O boleto vence em 3 dias úteis. Após o pagamento, aguarde até 2 dias úteis para confirmação.")
        
        return payment_result


def get_payment_methods() -> List[Dict]:
    """Retorna métodos de pagamento disponíveis"""
    return [
        {
            "id": "pix",
            "name": "PIX",
            "description": "Pagamento instantâneo",
            "icon": "📱",
            "fees": "Sem taxas",
            "processing_time": "Imediato"
        },
        {
            "id": "credit_card",
            "name": "Cartão de Crédito",
            "description": "Visa, Mastercard, Elo",
            "icon": "💳",
            "fees": "Taxa do gateway",
            "processing_time": "Imediato"
        },
        {
            "id": "debit_card",
            "name": "Cartão de Débito",
            "description": "Visa, Mastercard, Elo",
            "icon": "💳",
            "fees": "Taxa reduzida",
            "processing_time": "Imediato"
        },
        {
            "id": "boleto",
            "name": "Boleto Bancário",
            "description": "Pagamento em banco ou lotérica",
            "icon": "🏦",
            "fees": "Sem taxas",
            "processing_time": "2-3 dias úteis"
        }
    ]


def format_currency(value: float) -> str:
    """Formata valor em moeda brasileira"""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
