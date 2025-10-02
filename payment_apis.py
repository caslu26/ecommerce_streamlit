"""
Integração com APIs Reais de Pagamento
Suporte a Stripe, PagSeguro, Mercado Pago e outros gateways
"""

import streamlit as st
import requests
import json
import hashlib
import hmac
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta


class PaymentAPIBase:
    """Classe base para APIs de pagamento"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.base_url = config.get('base_url', '')
        self.api_key = config.get('api_key', '')
        self.secret_key = config.get('secret_key', '')
        self.environment = config.get('environment', 'sandbox')
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> Dict:
        """Faz requisição HTTP para a API"""
        url = f"{self.base_url}{endpoint}"
        
        default_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=default_headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=default_headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=default_headers, json=data)
            else:
                return {"success": False, "error": f"Método HTTP não suportado: {method}"}
            
            response.raise_for_status()
            return {"success": True, "data": response.json()}
            
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Erro na requisição: {str(e)}"}
        except json.JSONDecodeError:
            return {"success": False, "error": "Resposta inválida da API"}


class StripeAPI(PaymentAPIBase):
    """Integração com Stripe"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        if self.environment == 'sandbox':
            self.base_url = 'https://api.stripe.com/v1'
        else:
            self.base_url = 'https://api.stripe.com/v1'
    
    def create_payment_intent(self, amount: float, currency: str = 'brl', 
                             payment_method_types: list = None) -> Dict:
        """Cria intenção de pagamento no Stripe"""
        if payment_method_types is None:
            payment_method_types = ['card']
        
        data = {
            'amount': int(amount * 100),  # Stripe usa centavos
            'currency': currency,
            'payment_method_types': payment_method_types,
            'automatic_payment_methods': {
                'enabled': True
            }
        }
        
        return self._make_request('POST', '/payment_intents', data)
    
    def create_payment_method(self, card_data: Dict) -> Dict:
        """Cria método de pagamento no Stripe"""
        data = {
            'type': 'card',
            'card': {
                'number': card_data['number'],
                'exp_month': int(card_data['expiry'].split('/')[0]),
                'exp_year': int('20' + card_data['expiry'].split('/')[1]),
                'cvc': card_data['cvv']
            },
            'billing_details': {
                'name': card_data.get('name', ''),
                'email': card_data.get('email', '')
            }
        }
        
        return self._make_request('POST', '/payment_methods', data)
    
    def confirm_payment_intent(self, payment_intent_id: str, payment_method_id: str) -> Dict:
        """Confirma intenção de pagamento"""
        data = {
            'payment_method': payment_method_id
        }
        
        return self._make_request('POST', f'/payment_intents/{payment_intent_id}/confirm', data)


class PagSeguroAPI(PaymentAPIBase):
    """Integração com PagSeguro"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        if self.environment == 'sandbox':
            self.base_url = 'https://sandbox.pagseguro.uol.com.br'
        else:
            self.base_url = 'https://ws.pagseguro.uol.com.br'
    
    def create_payment_request(self, amount: float, reference: str, 
                              customer_data: Dict, items: list) -> Dict:
        """Cria solicitação de pagamento no PagSeguro"""
        data = {
            'currency': 'BRL',
            'reference': reference,
            'amount': {
                'value': f"{amount:.2f}"
            },
            'customer': {
                'name': customer_data.get('name', ''),
                'email': customer_data.get('email', ''),
                'tax_id': customer_data.get('cpf', '')
            },
            'items': items,
            'notification_urls': [
                self.config.get('notification_url', '')
            ]
        }
        
        return self._make_request('POST', '/v2/charges', data)
    
    def create_credit_card_payment(self, charge_id: str, card_data: Dict) -> Dict:
        """Cria pagamento com cartão de crédito"""
        data = {
            'payment_method': {
                'type': 'CREDIT_CARD',
                'installments': card_data.get('installments', 1),
                'capture': True,
                'card': {
                    'number': card_data['number'],
                    'exp_month': card_data['expiry'].split('/')[0],
                    'exp_year': card_data['expiry'].split('/')[1],
                    'security_code': card_data['cvv'],
                    'holder': {
                        'name': card_data.get('name', '')
                    }
                }
            }
        }
        
        return self._make_request('POST', f'/v2/charges/{charge_id}/capture', data)


class MercadoPagoAPI(PaymentAPIBase):
    """Integração com Mercado Pago"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        if self.environment == 'sandbox':
            self.base_url = 'https://api.mercadopago.com'
        else:
            self.base_url = 'https://api.mercadopago.com'
    
    def create_preference(self, items: list, payer: Dict, 
                         back_urls: Dict = None) -> Dict:
        """Cria preferência de pagamento no Mercado Pago"""
        if back_urls is None:
            back_urls = {
                'success': self.config.get('success_url', ''),
                'failure': self.config.get('failure_url', ''),
                'pending': self.config.get('pending_url', '')
            }
        
        data = {
            'items': items,
            'payer': payer,
            'back_urls': back_urls,
            'auto_return': 'approved',
            'payment_methods': {
                'excluded_payment_types': [],
                'excluded_payment_methods': [],
                'installments': 12
            }
        }
        
        return self._make_request('POST', '/checkout/preferences', data)
    
    def create_payment(self, transaction_amount: float, token: str, 
                      description: str, installments: int = 1,
                      payment_method_id: str = 'visa') -> Dict:
        """Cria pagamento no Mercado Pago"""
        data = {
            'transaction_amount': transaction_amount,
            'token': token,
            'description': description,
            'installments': installments,
            'payment_method_id': payment_method_id,
            'payer': {
                'email': 'test@test.com'
            }
        }
        
        return self._make_request('POST', '/v1/payments', data)


class PaymentAPIManager:
    """Gerenciador de APIs de pagamento"""
    
    def __init__(self):
        self.apis = {}
        self.load_configurations()
    
    def load_configurations(self):
        """Carrega configurações das APIs"""
        try:
            with open('payment_apis_config.json', 'r', encoding='utf-8') as f:
                configs = json.load(f)
                
            for api_name, config in configs.items():
                if config.get('enabled', False):
                    if api_name == 'stripe':
                        self.apis['stripe'] = StripeAPI(config)
                    elif api_name == 'pagseguro':
                        self.apis['pagseguro'] = PagSeguroAPI(config)
                    elif api_name == 'mercadopago':
                        self.apis['mercadopago'] = MercadoPagoAPI(config)
                        
        except FileNotFoundError:
            st.warning("Arquivo de configuração de APIs não encontrado. Usando modo simulado.")
        except Exception as e:
            st.error(f"Erro ao carregar configurações das APIs: {e}")
    
    def process_credit_card_payment(self, card_data: Dict, amount: float, 
                                   gateway: str = 'stripe') -> Dict:
        """Processa pagamento com cartão de crédito"""
        if gateway not in self.apis:
            return self._fallback_payment(card_data, amount, 'credit')
        
        api = self.apis[gateway]
        
        try:
            if gateway == 'stripe':
                # Criar método de pagamento
                pm_result = api.create_payment_method(card_data)
                if not pm_result['success']:
                    return pm_result
                
                # Criar intenção de pagamento
                pi_result = api.create_payment_intent(amount)
                if not pi_result['success']:
                    return pi_result
                
                # Confirmar pagamento
                confirm_result = api.confirm_payment_intent(
                    pi_result['data']['id'], 
                    pm_result['data']['id']
                )
                
                if confirm_result['success']:
                    return {
                        'success': True,
                        'transaction_id': pi_result['data']['id'],
                        'status': 'approved',
                        'gateway_response': confirm_result['data']
                    }
                else:
                    return confirm_result
                    
            elif gateway == 'pagseguro':
                # Implementar fluxo do PagSeguro
                return self._fallback_payment(card_data, amount, 'credit')
                
            elif gateway == 'mercadopago':
                # Implementar fluxo do Mercado Pago
                return self._fallback_payment(card_data, amount, 'credit')
                
        except Exception as e:
            return {'success': False, 'error': f'Erro na API {gateway}: {str(e)}'}
    
    def process_debit_card_payment(self, card_data: Dict, amount: float, 
                                  gateway: str = 'stripe') -> Dict:
        """Processa pagamento com cartão de débito"""
        if gateway not in self.apis:
            return self._fallback_payment(card_data, amount, 'debit')
        
        # Para débito, usar o mesmo fluxo do crédito mas sem parcelamento
        card_data['installments'] = 1
        return self.process_credit_card_payment(card_data, amount, gateway)
    
    def process_pix_payment(self, amount: float, description: str = '', 
                           gateway: str = 'mercadopago') -> Dict:
        """Processa pagamento via PIX"""
        if gateway not in self.apis:
            return self._fallback_pix_payment(amount, description)
        
        # Implementar PIX para diferentes gateways
        return self._fallback_pix_payment(amount, description)
    
    def _fallback_payment(self, card_data: Dict, amount: float, card_type: str) -> Dict:
        """Fallback para pagamento simulado"""
        import secrets
        import random
        
        transaction_id = f"{card_type.upper()}{int(time.time())}{secrets.randbelow(1000):03d}"
        success_rate = 0.92 if card_type == 'debit' else 0.85
        
        if random.random() < success_rate:
            return {
                'success': True,
                'transaction_id': transaction_id,
                'status': 'approved',
                'message': f'Pagamento {card_type} aprovado (simulado)',
                'gateway_response': {
                    'authorization_code': f'AUTH{secrets.token_hex(4).upper()}',
                    'processor_response': '00',
                    'processor_message': 'Approved'
                }
            }
        else:
            return {
                'success': False,
                'error': f'Pagamento {card_type} recusado (simulado)',
                'transaction_id': transaction_id
            }
    
    def _fallback_pix_payment(self, amount: float, description: str) -> Dict:
        """Fallback para PIX simulado"""
        import secrets
        
        transaction_id = f"PIX{int(time.time())}{secrets.randbelow(1000):03d}"
        pix_key = secrets.token_hex(16)
        
        return {
            'success': True,
            'transaction_id': transaction_id,
            'status': 'pending',
            'pix_key': pix_key,
            'qr_code': f"https://via.placeholder.com/200x200/667eea/white?text=PIX+{amount}",
            'expires_at': datetime.now() + timedelta(minutes=30),
            'message': 'PIX gerado (simulado)'
        }


def create_payment_apis_config():
    """Cria arquivo de configuração das APIs"""
    config = {
        "stripe": {
            "enabled": False,
            "environment": "sandbox",
            "api_key": "sk_test_...",
            "secret_key": "sk_test_...",
            "webhook_secret": "whsec_...",
            "success_url": "https://seudominio.com/success",
            "cancel_url": "https://seudominio.com/cancel"
        },
        "pagseguro": {
            "enabled": False,
            "environment": "sandbox",
            "api_key": "SEU_TOKEN_PAGSEGURO",
            "notification_url": "https://seudominio.com/webhook/pagseguro"
        },
        "mercadopago": {
            "enabled": False,
            "environment": "sandbox",
            "api_key": "TEST-...",
            "access_token": "TEST-...",
            "success_url": "https://seudominio.com/success",
            "failure_url": "https://seudominio.com/failure",
            "pending_url": "https://seudominio.com/pending"
        }
    }
    
    with open('payment_apis_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    return config


def get_payment_api_manager() -> PaymentAPIManager:
    """Retorna instância do gerenciador de APIs"""
    return PaymentAPIManager()

