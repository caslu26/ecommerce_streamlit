"""
Configuração do Sistema de Pagamento
Gerencia chaves PIX, dados bancários e configurações de gateway
"""

import streamlit as st
import json
import os
from typing import Dict, Optional
from database import get_conn


class PaymentConfig:
    """Classe para gerenciar configurações de pagamento"""
    
    def __init__(self):
        self.config_file = "payment_config.json"
        self.load_config()
    
    def load_config(self) -> Dict:
        """Carrega configurações do arquivo"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except:
                self.config = self.get_default_config()
        else:
            self.config = self.get_default_config()
            self.save_config()
        return self.config
    
    def save_config(self) -> bool:
        """Salva configurações no arquivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar configurações: {e}")
            return False
    
    def get_default_config(self) -> Dict:
        """Retorna configuração padrão"""
        return {
            "pix": {
                "enabled": True,
                "chave_pix": "",
                "nome_recebedor": "E-Store",
                "cidade": "São Paulo",
                "descricao": "Pagamento E-commerce"
            },
            "boleto": {
                "enabled": True,
                "banco": "341",  # Itaú
                "agencia": "1234",
                "conta": "12345-6",
                "cedente": "E-Store LTDA",
                "cnpj": "12.345.678/0001-90",
                "endereco": "Rua das Flores, 123 - São Paulo/SP",
                "dias_vencimento": 3
            },
            "cartao": {
                "enabled": True,
                "gateway": "simulado",
                "merchant_id": "MERCHANT123",
                "api_key": "API_KEY_SIMULADA",
                "webhook_url": "https://seudominio.com/webhook",
                "taxa_porcentagem": 2.99,
                "taxa_fixa": 0.50
            },
            "notificacoes": {
                "email": {
                    "enabled": True,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "email": "contato@estore.com",
                    "senha": ""
                },
                "webhook": {
                    "enabled": False,
                    "url": "",
                    "secret": ""
                }
            }
        }
    
    def get_pix_config(self) -> Dict:
        """Retorna configuração do PIX"""
        return self.config.get("pix", {})
    
    def get_boleto_config(self) -> Dict:
        """Retorna configuração do boleto"""
        return self.config.get("boleto", {})
    
    def get_cartao_config(self) -> Dict:
        """Retorna configuração do cartão"""
        return self.config.get("cartao", {})
    
    def update_pix_config(self, chave_pix: str, nome_recebedor: str, cidade: str, descricao: str = "") -> bool:
        """Atualiza configuração do PIX"""
        self.config["pix"]["chave_pix"] = chave_pix
        self.config["pix"]["nome_recebedor"] = nome_recebedor
        self.config["pix"]["cidade"] = cidade
        if descricao:
            self.config["pix"]["descricao"] = descricao
        return self.save_config()
    
    def update_boleto_config(self, banco: str, agencia: str, conta: str, cedente: str, cnpj: str, dias_vencimento: int = 3) -> bool:
        """Atualiza configuração do boleto"""
        self.config["boleto"]["banco"] = banco
        self.config["boleto"]["agencia"] = agencia
        self.config["boleto"]["conta"] = conta
        self.config["boleto"]["cedente"] = cedente
        self.config["boleto"]["cnpj"] = cnpj
        self.config["boleto"]["dias_vencimento"] = dias_vencimento
        return self.save_config()
    
    def update_cartao_config(self, merchant_id: str, taxa_porcentagem: float, taxa_fixa: float, gateway: str = "Simulado") -> bool:
        """Atualiza configuração do cartão"""
        self.config["cartao"]["merchant_id"] = merchant_id
        self.config["cartao"]["taxa_porcentagem"] = taxa_porcentagem
        self.config["cartao"]["taxa_fixa"] = taxa_fixa
        self.config["cartao"]["gateway"] = gateway
        return self.save_config()
    
    def clear_pix_config(self) -> bool:
        """Limpa configuração do PIX"""
        self.config["pix"] = {
            "enabled": False,
            "chave_pix": "",
            "nome_recebedor": "",
            "cidade": "",
            "descricao": ""
        }
        return self.save_config()
    
    def clear_boleto_config(self) -> bool:
        """Limpa configuração do Boleto"""
        self.config["boleto"] = {
            "enabled": False,
            "banco": "",
            "agencia": "",
            "conta": "",
            "cedente": "",
            "cnpj": "",
            "dias_vencimento": 3
        }
        return self.save_config()
    
    def clear_cartao_config(self) -> bool:
        """Limpa configuração do Cartão"""
        self.config["cartao"] = {
            "enabled": False,
            "merchant_id": "",
            "taxa_porcentagem": 3.5,
            "taxa_fixa": 0.39,
            "gateway": "Simulado"
        }
        return self.save_config()


class PaymentGateway:
    """Simulador de Gateway de Pagamento"""
    
    def __init__(self, config: PaymentConfig):
        self.config = config
    
    def process_pix_payment(self, amount: float, description: str = "") -> Dict:
        """Processa pagamento PIX"""
        pix_config = self.config.get_pix_config()
        
        if not pix_config.get("chave_pix"):
            return {
                "success": False,
                "error": "Chave PIX não configurada. Configure no painel administrativo."
            }
        
        # Simular processamento PIX
        import secrets
        import time
        
        transaction_id = f"PIX{int(time.time())}{secrets.randbelow(1000):03d}"
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "status": "pending",
            "payment_method": "PIX",
            "pix_key": pix_config["chave_pix"],
            "qr_code": self._generate_pix_qr_code(amount, pix_config),
            "expires_at": time.time() + 1800,  # 30 minutos
            "message": f"PIX gerado para {pix_config['nome_recebedor']}"
        }
    
    def process_boleto_payment(self, amount: float, due_date_days: int = 3) -> Dict:
        """Processa pagamento via boleto"""
        boleto_config = self.config.get_boleto_config()
        
        if not boleto_config.get("banco"):
            return {
                "success": False,
                "error": "Configuração bancária não encontrada. Configure no painel administrativo."
            }
        
        # Gerar boleto
        import secrets
        import time
        from datetime import datetime, timedelta
        
        transaction_id = f"BOL{int(time.time())}{secrets.randbelow(1000):03d}"
        boleto_number = self._generate_boleto_number(boleto_config)
        due_date = datetime.now() + timedelta(days=due_date_days)
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "status": "pending",
            "payment_method": "Boleto Bancário",
            "boleto_number": boleto_number,
            "barcode": self._generate_boleto_barcode(boleto_number, amount, due_date),
            "due_date": due_date.timestamp(),
            "cedente": boleto_config["cedente"],
            "cnpj": boleto_config["cnpj"],
            "message": f"Boleto gerado - Banco {boleto_config['banco']}"
        }
    
    def process_credit_card_payment(self, card_data: Dict) -> Dict:
        """Processa pagamento com cartão de crédito"""
        cartao_config = self.config.get_cartao_config()
        
        # Simular validação e processamento
        import secrets
        import time
        import random
        
        transaction_id = f"CC{int(time.time())}{secrets.randbelow(1000):03d}"
        
        # Simular diferentes cenários (85% aprovação)
        if random.random() < 0.85:
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": "approved",
                "payment_method": "Cartão de Crédito",
                "card_last_four": card_data["number"][-4:],
                "card_brand": self._detect_card_brand(card_data["number"]),
                "installments": card_data.get("installments", 1),
                "authorization_code": f"AUTH{secrets.token_hex(4).upper()}",
                "processor_response": "00",
                "processor_message": "Approved",
                "gateway_response": {
                    "merchant_id": cartao_config.get("merchant_id", "MERCHANT123"),
                    "amount": card_data["amount"],
                    "installments": card_data.get("installments", 1),
                    "card_brand": self._detect_card_brand(card_data["number"]),
                    "last_four": card_data["number"][-4:],
                    "processing_fee": self._calculate_processing_fee(card_data["amount"], cartao_config)
                }
            }
        else:
            return {
                "success": False,
                "transaction_id": transaction_id,
                "error": "Pagamento recusado pelo banco",
                "processor_response": "05",
                "processor_message": "Do not honor"
            }
    
    def process_debit_card_payment(self, card_data: Dict) -> Dict:
        """Processa pagamento com cartão de débito"""
        cartao_config = self.config.get_cartao_config()
        
        # Simular validação e processamento
        import secrets
        import time
        import random
        
        transaction_id = f"DC{int(time.time())}{secrets.randbelow(1000):03d}"
        
        # Simular diferentes cenários (92% aprovação para débito)
        if random.random() < 0.92:
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": "approved",
                "payment_method": "Cartão de Débito",
                "card_last_four": card_data["number"][-4:],
                "card_brand": self._detect_card_brand(card_data["number"]),
                "authorization_code": f"AUTH{secrets.token_hex(4).upper()}",
                "processor_response": "00",
                "processor_message": "Approved",
                "gateway_response": {
                    "merchant_id": cartao_config.get("merchant_id", "MERCHANT123"),
                    "amount": card_data["amount"],
                    "installments": 1,  # Débito sempre à vista
                    "card_brand": self._detect_card_brand(card_data["number"]),
                    "last_four": card_data["number"][-4:],
                    "processing_fee": self._calculate_debit_processing_fee(card_data["amount"], cartao_config),
                    "card_type": "debit"
                }
            }
        else:
            return {
                "success": False,
                "transaction_id": transaction_id,
                "error": "Saldo insuficiente ou cartão recusado",
                "processor_response": "51",
                "processor_message": "Insufficient funds"
            }
    
    def _generate_pix_qr_code(self, amount: float, pix_config: Dict) -> str:
        """Gera QR Code PIX"""
        # Dados do PIX no formato EMV
        pix_data = {
            "amount": amount,
            "key": pix_config["chave_pix"],
            "merchant": pix_config["nome_recebedor"],
            "city": pix_config["cidade"],
            "description": pix_config.get("descricao", "Pagamento E-commerce")
        }
        
        # Tentar gerar QR Code real
        try:
            import qrcode
            import io
            import base64
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(pix_data))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
        except ImportError:
            # Fallback para placeholder
            return f"https://via.placeholder.com/200x200/667eea/white?text=PIX+{amount}"
    
    def _generate_boleto_number(self, boleto_config: Dict) -> str:
        """Gera número do boleto"""
        import secrets
        banco = boleto_config["banco"]
        agencia = boleto_config["agencia"].zfill(4)
        conta = boleto_config["conta"].replace("-", "").zfill(8)
        
        # Gerar número sequencial
        sequencial = f"{secrets.randbelow(100000):05d}"
        
        return f"{banco}.{agencia}.{conta}.{sequencial}"
    
    def _generate_boleto_barcode(self, boleto_number: str, amount: float, due_date) -> str:
        """Gera código de barras do boleto"""
        # Formato simplificado do código de barras
        banco = boleto_number.split('.')[0]
        valor = f"{amount:010.2f}".replace('.', '').replace(',', '')
        vencimento = due_date.strftime('%d%m%Y')
        
        # Gerar código de barras (formato simplificado)
        barcode = f"{banco}9{vencimento}{valor}"
        
        # Adicionar dígitos verificadores (simplificado)
        barcode += "00"  # Dígitos verificadores simulados
        
        return barcode
    
    def _detect_card_brand(self, card_number: str) -> str:
        """Detecta a bandeira do cartão"""
        card_number = card_number.replace(' ', '').replace('-', '')
        
        if card_number.startswith('4'):
            return 'Visa'
        elif card_number.startswith(('51', '52', '53', '54', '55')):
            return 'Mastercard'
        elif card_number.startswith(('34', '37')):
            return 'American Express'
        elif card_number.startswith(('30', '36', '38')):
            return 'Diners Club'
        elif card_number.startswith('6011'):
            return 'Discover'
        else:
            return 'Elo'
    
    def _calculate_processing_fee(self, amount: float, cartao_config: Dict) -> float:
        """Calcula taxa de processamento para crédito"""
        taxa_porcentagem = cartao_config.get("taxa_porcentagem", 2.99)
        taxa_fixa = cartao_config.get("taxa_fixa", 0.50)
        
        return (amount * taxa_porcentagem / 100) + taxa_fixa
    
    def _calculate_debit_processing_fee(self, amount: float, cartao_config: Dict) -> float:
        """Calcula taxa de processamento para débito (reduzida)"""
        # Taxa reduzida para débito (50% da taxa de crédito)
        taxa_porcentagem = cartao_config.get("taxa_porcentagem", 2.99) * 0.5
        taxa_fixa = cartao_config.get("taxa_fixa", 0.50) * 0.5
        
        return (amount * taxa_porcentagem / 100) + taxa_fixa


def render_payment_config_page():
    """Renderiza página de configuração de pagamentos"""
    st.markdown("## ⚙️ Configuração de Pagamentos")
    
    config = PaymentConfig()
    
    # Tabs para diferentes configurações
    tab1, tab2, tab3, tab4 = st.tabs(["📱 PIX", "🏦 Boleto", "💳 Cartão", "📧 Notificações"])
    
    with tab1:
        st.markdown("### 📱 Configuração PIX")
        
        pix_config = config.get_pix_config()
        
        with st.form("pix_config_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                chave_pix = st.text_input(
                    "🔑 Chave PIX",
                    value=pix_config.get("chave_pix", ""),
                    placeholder="CPF, CNPJ, email ou chave aleatória",
                    help="Digite sua chave PIX (CPF, CNPJ, email ou chave aleatória)"
                )
                
                nome_recebedor = st.text_input(
                    "👤 Nome do Recebedor",
                    value=pix_config.get("nome_recebedor", ""),
                    placeholder="Nome da empresa ou pessoa"
                )
            
            with col2:
                cidade = st.text_input(
                    "🏙️ Cidade",
                    value=pix_config.get("cidade", ""),
                    placeholder="Cidade do recebedor"
                )
                
                descricao = st.text_input(
                    "📝 Descrição",
                    value=pix_config.get("descricao", ""),
                    placeholder="Descrição do pagamento"
                )
            
            if st.form_submit_button("💾 Salvar Configuração PIX", use_container_width=True):
                if chave_pix and nome_recebedor and cidade:
                    if config.update_pix_config(chave_pix, nome_recebedor, cidade):
                        st.success("✅ Configuração PIX salva com sucesso!")
                    else:
                        st.error("❌ Erro ao salvar configuração PIX!")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios!")
        
        # Mostrar configuração atual
        if pix_config.get("chave_pix"):
            st.markdown("### 📋 Configuração PIX Atual")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.info(f"""
                **🔑 Chave PIX:** `{pix_config['chave_pix']}`  
                **👤 Recebedor:** {pix_config['nome_recebedor']}  
                **🏙️ Cidade:** {pix_config['cidade']}
                """)
            
            with col2:
                st.markdown("**⚙️ Ações:**")
                
                if st.button("🔧 Editar PIX", key="edit_pix", use_container_width=True, type="primary"):
                    st.session_state.edit_pix_config = True
                    st.rerun()
                
                if st.button("🗑️ Excluir PIX", key="delete_pix", use_container_width=True, type="secondary"):
                    st.session_state.delete_pix_config = True
                    st.rerun()
        
        # Modal de confirmação de exclusão PIX
        if st.session_state.get('delete_pix_config', False):
            st.markdown("---")
            st.markdown("### ⚠️ Confirmar Exclusão PIX")
            st.warning("**Você tem certeza que deseja excluir a configuração PIX?**")
            st.info("💡 **Importante:** Isso desabilitará completamente os pagamentos via PIX.")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("✅ Sim, Excluir PIX", key="confirm_delete_pix", type="primary", use_container_width=True):
                    if config.clear_pix_config():
                        st.success("✅ Configuração PIX excluída com sucesso!")
                        st.session_state.pop('delete_pix_config', None)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao excluir configuração PIX!")
            
            with col2:
                if st.button("❌ Cancelar", key="cancel_delete_pix", use_container_width=True):
                    st.session_state.pop('delete_pix_config', None)
                    st.rerun()
        
        # Formulário de edição PIX
        if st.session_state.get('edit_pix_config', False):
            st.markdown("---")
            st.markdown("### ✏️ Editando Configuração PIX")
            
            if st.button("❌ Cancelar Edição PIX", key="cancel_edit_pix"):
                st.session_state.pop('edit_pix_config', None)
                st.rerun()
            
            with st.form("edit_pix_config_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_chave_pix = st.text_input(
                        "🔑 Nova Chave PIX",
                        value=pix_config.get("chave_pix", ""),
                        placeholder="CPF, CNPJ, email ou chave aleatória"
                    )
                    
                    new_nome_recebedor = st.text_input(
                        "👤 Novo Nome do Recebedor",
                        value=pix_config.get("nome_recebedor", ""),
                        placeholder="Nome da empresa ou pessoa"
                    )
                
                with col2:
                    new_cidade = st.text_input(
                        "🏙️ Nova Cidade",
                        value=pix_config.get("cidade", ""),
                        placeholder="Cidade do recebedor"
                    )
                    
                    new_descricao = st.text_input(
                        "📝 Nova Descrição",
                        value=pix_config.get("descricao", ""),
                        placeholder="Descrição do pagamento"
                    )
                
                if st.form_submit_button("💾 Salvar Alterações PIX", use_container_width=True):
                    if new_chave_pix and new_nome_recebedor and new_cidade:
                        if config.update_pix_config(new_chave_pix, new_nome_recebedor, new_cidade, new_descricao):
                            st.success("✅ Configuração PIX atualizada com sucesso!")
                            st.session_state.pop('edit_pix_config', None)
                            st.rerun()
                        else:
                            st.error("❌ Erro ao atualizar configuração PIX!")
                    else:
                        st.error("❌ Preencha todos os campos obrigatórios!")
    
    with tab2:
        st.markdown("### 🏦 Configuração Boleto Bancário")
        
        boleto_config = config.get_boleto_config()
        
        with st.form("boleto_config_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                banco = st.selectbox(
                    "🏦 Banco",
                    options=["341", "001", "104", "237", "033", "756"],
                    format_func=lambda x: {
                        "341": "Itaú (341)",
                        "001": "Banco do Brasil (001)",
                        "104": "Caixa Econômica (104)",
                        "237": "Bradesco (237)",
                        "033": "Santander (033)",
                        "756": "Sicoob (756)"
                    }.get(x, x),
                    index=0 if boleto_config.get("banco") == "341" else 0
                )
                
                agencia = st.text_input(
                    "🏢 Agência",
                    value=boleto_config.get("agencia", ""),
                    placeholder="1234"
                )
                
                conta = st.text_input(
                    "💳 Conta",
                    value=boleto_config.get("conta", ""),
                    placeholder="12345-6"
                )
            
            with col2:
                cedente = st.text_input(
                    "🏢 Nome do Cedente",
                    value=boleto_config.get("cedente", ""),
                    placeholder="Nome da empresa"
                )
                
                cnpj = st.text_input(
                    "📄 CNPJ",
                    value=boleto_config.get("cnpj", ""),
                    placeholder="12.345.678/0001-90"
                )
                
                dias_vencimento = st.number_input(
                    "📅 Dias para Vencimento",
                    value=boleto_config.get("dias_vencimento", 3),
                    min_value=1,
                    max_value=30
                )
            
            if st.form_submit_button("💾 Salvar Configuração Boleto", use_container_width=True):
                if banco and agencia and conta and cedente and cnpj:
                    if config.update_boleto_config(banco, agencia, conta, cedente, cnpj):
                        st.success("✅ Configuração de boleto salva com sucesso!")
                    else:
                        st.error("❌ Erro ao salvar configuração de boleto!")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios!")
        
        # Mostrar configuração atual
        if boleto_config.get("banco"):
            st.markdown("### 📋 Configuração Boleto Atual")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.info(f"""
                **🏦 Banco:** {boleto_config['banco']}  
                **🏢 Agência:** {boleto_config['agencia']}  
                **💳 Conta:** {boleto_config['conta']}  
                **🏢 Cedente:** {boleto_config['cedente']}  
                **📄 CNPJ:** {boleto_config['cnpj']}
                """)
            
            with col2:
                st.markdown("**⚙️ Ações:**")
                
                if st.button("🔧 Editar Boleto", key="edit_boleto", use_container_width=True, type="primary"):
                    st.session_state.edit_boleto_config = True
                    st.rerun()
                
                if st.button("🗑️ Excluir Boleto", key="delete_boleto", use_container_width=True, type="secondary"):
                    st.session_state.delete_boleto_config = True
                    st.rerun()
        
        # Modal de confirmação de exclusão Boleto
        if st.session_state.get('delete_boleto_config', False):
            st.markdown("---")
            st.markdown("### ⚠️ Confirmar Exclusão Boleto")
            st.warning("**Você tem certeza que deseja excluir a configuração de Boleto?**")
            st.info("💡 **Importante:** Isso desabilitará completamente os pagamentos via Boleto.")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("✅ Sim, Excluir Boleto", key="confirm_delete_boleto", type="primary", use_container_width=True):
                    if config.clear_boleto_config():
                        st.success("✅ Configuração Boleto excluída com sucesso!")
                        st.session_state.pop('delete_boleto_config', None)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao excluir configuração Boleto!")
            
            with col2:
                if st.button("❌ Cancelar", key="cancel_delete_boleto", use_container_width=True):
                    st.session_state.pop('delete_boleto_config', None)
                    st.rerun()
        
        # Formulário de edição Boleto
        if st.session_state.get('edit_boleto_config', False):
            st.markdown("---")
            st.markdown("### ✏️ Editando Configuração Boleto")
            
            if st.button("❌ Cancelar Edição Boleto", key="cancel_edit_boleto"):
                st.session_state.pop('edit_boleto_config', None)
                st.rerun()
            
            with st.form("edit_boleto_config_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_banco = st.selectbox(
                        "🏦 Novo Banco",
                        options=["341", "001", "104", "237", "033", "756"],
                        format_func=lambda x: {
                            "341": "Itaú (341)",
                            "001": "Banco do Brasil (001)",
                            "104": "Caixa Econômica (104)",
                            "237": "Bradesco (237)",
                            "033": "Santander (033)",
                            "756": "Sicoob (756)"
                        }.get(x, x),
                        index=["341", "001", "104", "237", "033", "756"].index(boleto_config.get("banco", "341"))
                    )
                    
                    new_agencia = st.text_input(
                        "🏢 Nova Agência",
                        value=boleto_config.get("agencia", ""),
                        placeholder="1234"
                    )
                    
                    new_conta = st.text_input(
                        "💳 Nova Conta",
                        value=boleto_config.get("conta", ""),
                        placeholder="12345-6"
                    )
                
                with col2:
                    new_cedente = st.text_input(
                        "🏢 Novo Nome do Cedente",
                        value=boleto_config.get("cedente", ""),
                        placeholder="Nome da empresa"
                    )
                    
                    new_cnpj = st.text_input(
                        "📄 Novo CNPJ",
                        value=boleto_config.get("cnpj", ""),
                        placeholder="12.345.678/0001-90"
                    )
                    
                    new_dias_vencimento = st.number_input(
                        "📅 Novos Dias para Vencimento",
                        value=boleto_config.get("dias_vencimento", 3),
                        min_value=1,
                        max_value=30
                    )
                
                if st.form_submit_button("💾 Salvar Alterações Boleto", use_container_width=True):
                    if new_banco and new_agencia and new_conta and new_cedente and new_cnpj:
                        if config.update_boleto_config(new_banco, new_agencia, new_conta, new_cedente, new_cnpj, new_dias_vencimento):
                            st.success("✅ Configuração Boleto atualizada com sucesso!")
                            st.session_state.pop('edit_boleto_config', None)
                            st.rerun()
                        else:
                            st.error("❌ Erro ao atualizar configuração Boleto!")
                    else:
                        st.error("❌ Preencha todos os campos obrigatórios!")
    
    with tab3:
        st.markdown("### 💳 Configuração Gateway de Cartão")
        
        cartao_config = config.get_cartao_config()
        
        with st.form("cartao_config_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                merchant_id = st.text_input(
                    "🆔 Merchant ID",
                    value=cartao_config.get("merchant_id", ""),
                    placeholder="ID do comerciante"
                )
                
                api_key = st.text_input(
                    "🔑 API Key",
                    value=cartao_config.get("api_key", ""),
                    type="password",
                    placeholder="Chave da API"
                )
            
            with col2:
                taxa_porcentagem = st.number_input(
                    "📊 Taxa (%)",
                    value=cartao_config.get("taxa_porcentagem", 2.99),
                    min_value=0.0,
                    max_value=10.0,
                    step=0.01,
                    format="%.2f"
                )
                
                taxa_fixa = st.number_input(
                    "💰 Taxa Fixa (R$)",
                    value=cartao_config.get("taxa_fixa", 0.50),
                    min_value=0.0,
                    step=0.01,
                    format="%.2f"
                )
            
            if st.form_submit_button("💾 Salvar Configuração Cartão", use_container_width=True):
                if merchant_id and api_key:
                    if config.update_cartao_config(merchant_id, api_key, taxa_porcentagem):
                        st.success("✅ Configuração de cartão salva com sucesso!")
                    else:
                        st.error("❌ Erro ao salvar configuração de cartão!")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios!")
        
        # Mostrar configuração atual
        if cartao_config.get("merchant_id"):
            st.markdown("### 📋 Configuração Cartão Atual")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.info(f"""
                **🆔 Merchant ID:** {cartao_config['merchant_id']}  
                **📊 Taxa:** {cartao_config['taxa_porcentagem']}% + R$ {cartao_config['taxa_fixa']}  
                **🔧 Gateway:** {cartao_config.get('gateway', 'Simulado')}
                """)
            
            with col2:
                st.markdown("**⚙️ Ações:**")
                
                if st.button("🔧 Editar Cartão", key="edit_cartao", use_container_width=True, type="primary"):
                    st.session_state.edit_cartao_config = True
                    st.rerun()
                
                if st.button("🗑️ Excluir Cartão", key="delete_cartao", use_container_width=True, type="secondary"):
                    st.session_state.delete_cartao_config = True
                    st.rerun()
        
        # Modal de confirmação de exclusão Cartão
        if st.session_state.get('delete_cartao_config', False):
            st.markdown("---")
            st.markdown("### ⚠️ Confirmar Exclusão Cartão")
            st.warning("**Você tem certeza que deseja excluir a configuração de Cartão?**")
            st.info("💡 **Importante:** Isso desabilitará completamente os pagamentos via Cartão de Crédito e Débito.")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("✅ Sim, Excluir Cartão", key="confirm_delete_cartao", type="primary", use_container_width=True):
                    if config.clear_cartao_config():
                        st.success("✅ Configuração Cartão excluída com sucesso!")
                        st.session_state.pop('delete_cartao_config', None)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao excluir configuração Cartão!")
            
            with col2:
                if st.button("❌ Cancelar", key="cancel_delete_cartao", use_container_width=True):
                    st.session_state.pop('delete_cartao_config', None)
                    st.rerun()
        
        # Formulário de edição Cartão
        if st.session_state.get('edit_cartao_config', False):
            st.markdown("---")
            st.markdown("### ✏️ Editando Configuração Cartão")
            
            if st.button("❌ Cancelar Edição Cartão", key="cancel_edit_cartao"):
                st.session_state.pop('edit_cartao_config', None)
                st.rerun()
            
            with st.form("edit_cartao_config_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_merchant_id = st.text_input(
                        "🆔 Novo Merchant ID",
                        value=cartao_config.get("merchant_id", ""),
                        placeholder="MERCHANT123456"
                    )
                    
                    new_taxa_porcentagem = st.number_input(
                        "📊 Nova Taxa (%)",
                        value=cartao_config.get("taxa_porcentagem", 3.5),
                        min_value=0.0,
                        max_value=10.0,
                        step=0.1,
                        format="%.2f"
                    )
                
                with col2:
                    new_taxa_fixa = st.number_input(
                        "💰 Nova Taxa Fixa (R$)",
                        value=cartao_config.get("taxa_fixa", 0.39),
                        min_value=0.0,
                        step=0.01,
                        format="%.2f"
                    )
                    
                    new_gateway = st.selectbox(
                        "🔧 Novo Gateway",
                        options=["Simulado", "Stripe", "PagSeguro", "Mercado Pago"],
                        index=["Simulado", "Stripe", "PagSeguro", "Mercado Pago"].index(cartao_config.get("gateway", "Simulado"))
                    )
                
                if st.form_submit_button("💾 Salvar Alterações Cartão", use_container_width=True):
                    if new_merchant_id:
                        if config.update_cartao_config(new_merchant_id, new_taxa_porcentagem, new_taxa_fixa, new_gateway):
                            st.success("✅ Configuração Cartão atualizada com sucesso!")
                            st.session_state.pop('edit_cartao_config', None)
                            st.rerun()
                        else:
                            st.error("❌ Erro ao atualizar configuração Cartão!")
                    else:
                        st.error("❌ Preencha o Merchant ID!")
    
    with tab4:
        st.markdown("### 📧 Configuração de Notificações")
        
        st.info("""
        **📧 Email:** Configure SMTP para envio de notificações  
        **🔗 Webhook:** Configure URL para notificações em tempo real  
        **📱 SMS:** Integração com provedores de SMS (futuro)
        """)
        
        # Configuração de email
        st.markdown("#### 📧 Configuração de Email")
        email_config = config.config.get("notificacoes", {}).get("email", {})
        
        with st.form("email_config_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                smtp_server = st.text_input(
                    "📧 Servidor SMTP",
                    value=email_config.get("smtp_server", ""),
                    placeholder="smtp.gmail.com"
                )
                
                smtp_port = st.number_input(
                    "🔌 Porta SMTP",
                    value=email_config.get("smtp_port", 587),
                    min_value=1,
                    max_value=65535
                )
            
            with col2:
                email = st.text_input(
                    "📬 Email",
                    value=email_config.get("email", ""),
                    placeholder="contato@estore.com"
                )
                
                senha = st.text_input(
                    "🔑 Senha",
                    value=email_config.get("senha", ""),
                    type="password",
                    placeholder="Senha do email"
                )
            
            if st.form_submit_button("💾 Salvar Configuração Email", use_container_width=True):
                st.success("✅ Configuração de email salva! (Funcionalidade em desenvolvimento)")
        
        # Configuração de webhook
        st.markdown("#### 🔗 Configuração de Webhook")
        webhook_config = config.config.get("notificacoes", {}).get("webhook", {})
        
        with st.form("webhook_config_form"):
            webhook_url = st.text_input(
                "🔗 URL do Webhook",
                value=webhook_config.get("url", ""),
                placeholder="https://seudominio.com/webhook"
            )
            
            webhook_secret = st.text_input(
                "🔐 Secret do Webhook",
                value=webhook_config.get("secret", ""),
                type="password",
                placeholder="Chave secreta para validação"
            )
            
            if st.form_submit_button("💾 Salvar Configuração Webhook", use_container_width=True):
                st.success("✅ Configuração de webhook salva! (Funcionalidade em desenvolvimento)")


def get_payment_gateway() -> PaymentGateway:
    """Retorna instância do gateway de pagamento"""
    config = PaymentConfig()
    return PaymentGateway(config)

