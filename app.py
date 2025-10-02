import streamlit as st
from database import *
from payment_system import PaymentUI, PaymentProcessor, get_payment_methods
import io
import base64
import uuid
import os
import json
import time
from datetime import datetime
import bcrypt
import pandas as pd
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Função para limpeza automática de cache
def auto_clear_cache():
    """Limpa automaticamente o cache do Streamlit em intervalos regulares"""
    current_time = time.time()
    
    # Verificar se já passou tempo suficiente desde a última limpeza
    if 'last_cache_clear' not in st.session_state:
        st.session_state.last_cache_clear = current_time
    
    # Limpar cache a cada 5 minutos (300 segundos)
    if current_time - st.session_state.last_cache_clear > 300:
        st.cache_data.clear()
        st.session_state.last_cache_clear = current_time
        
    # Limpar dados de pagamento antigos da sessão
    if 'payment_result' in st.session_state:
        # Se o resultado do pagamento tem mais de 10 minutos, limpar
        if hasattr(st.session_state, 'payment_timestamp'):
            if current_time - st.session_state.payment_timestamp > 600:  # 10 minutos
                del st.session_state.payment_result
                if 'payment_timestamp' in st.session_state:
                    del st.session_state.payment_timestamp

def get_status_display(status):
    """Retorna o status formatado para exibição"""
    status_map = {
        'pending': '⏳ Aguardando Pagamento',
        'approved': '✅ Pago',
        'failed': '❌ Falhou',
        'cancelled': '🚫 Cancelado',
        'processing': '🔄 Processando'
    }
    return status_map.get(status, status)

# Configuração da página
st.set_page_config(
    page_title="E-Store | E-commerce Moderno",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado moderno
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 2rem;
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .product-card {
        border: none;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 0.5rem;
        transition: all 0.3s ease;
        background: linear-gradient(145deg, #ffffff, #f8fafc);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        position: relative;
        overflow: hidden;
    }
    
    .product-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
    
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15);
    }
    
    .product-card img {
        border-radius: 8px;
        transition: transform 0.3s ease;
    }
    
    .product-card:hover img {
        transform: scale(1.05);
    }
    
    .price-tag {
        font-size: 1.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #10b981, #059669);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .cart-counter {
        position: absolute;
        top: -8px;
        right: -8px;
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: bold;
        z-index: 10;
    }
    
    .header-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        border-radius: 12px;
        color: white;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .header-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    .search-bar {
        border: 2px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        font-size: 1rem;
        transition: all 0.3s ease;
        background: linear-gradient(145deg, #ffffff, #f9fafb);
    }
    
    .search-bar:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        outline: none;
    }
    
    .category-filter {
        background: linear-gradient(135deg, #f8fafc, #e2e8f0);
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        transition: all 0.3s ease;
    }
    
    .cart-item {
        background: linear-gradient(145deg, #ffffff, #f8fafc);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .cart-item:hover {
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
    
    .checkout-card {
        background: linear-gradient(145deg, #ffffff, #f0f9ff);
        border-radius: 16px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
        border: 1px solid #e0f2fe;
    }
    
    .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .notification {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
    }
    
    .error-notification {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
    }
</style>
""", unsafe_allow_html=True)


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed)


def login_page():
    """Página de login com opção de cadastro"""
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1 style='color: #667eea; margin: 0; font-size: 2.5rem;'>🔑 Acesso à Conta</h1>
        <p style='color: #6b7280; margin: 0.5rem 0;'>Faça login ou crie uma nova conta</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão voltar
    if st.button("← Voltar ao Início", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()
    
    # Tabs para Login e Cadastro
    tab_login, tab_register = st.tabs(["🔑 Login", "📝 Cadastro"])
    
    with tab_login:
        # Container centralizado para o formulário de login
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div style='background: linear-gradient(145deg, #ffffff, #f8fafc); 
                        padding: 2rem; border-radius: 16px; margin: 1rem 0; 
                        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);'>
            """, unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                st.markdown("### 🔐 Dados de Acesso")
                
                username = st.text_input(
                    "👤 Nome de usuário", 
                    placeholder="Digite seu nome de usuário",
                    help="Digite o nome de usuário que você criou na conta"
                )
                
                password = st.text_input(
                    "🔑 Senha", 
                    type="password", 
                    placeholder="Digite sua senha",
                    help="Digite a senha da sua conta"
                )
                
                # Opções adicionais
                remember_me = st.checkbox("Lembrar de mim")
                
                st.markdown("---")
                
                login_btn = st.form_submit_button("🔓 Entrar na Conta", use_container_width=True, type="primary")
                
                if login_btn:
                    if username and password:
                        user = authenticate_user(username, password)
                        if user:
                            st.session_state.user_id = user['id']
                            st.session_state.username = user['username']
                            st.session_state.role = user['role']
                            st.session_state.first_name = user['first_name']
                            
                            # Se vem do checkout, transferir carrinho de sessão
                            if st.session_state.get('from_checkout', False):
                                if 'session_cart' in st.session_state:
                                    for item in st.session_state.session_cart:
                                        add_to_cart(user['id'], item['product_id'], item['quantity'])
                                    del st.session_state.session_cart
                                st.session_state.page = "checkout"
                                st.session_state.pop('from_checkout', None)
                            else:
                                st.session_state.page = "home"
                            
                            st.success(f"✅ Bem-vindo de volta, {user['first_name']}!")
                            st.rerun()
                        else:
                            st.error("❌ Credenciais inválidas! Verifique seu usuário e senha.")
                    else:
                        st.error("❌ Preencha todos os campos!")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Botão "Esqueci minha senha" fora do formulário
            st.markdown("""
            <div style='text-align: center; margin: 1rem 0;'>
            """, unsafe_allow_html=True)
            
            if st.button("🔑 Esqueci minha senha", help="Funcionalidade em desenvolvimento"):
                st.info("📧 Funcionalidade de recuperação de senha será implementada em breve!")
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    with tab_register:
        # Container centralizado para o formulário de cadastro
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div style='background: linear-gradient(145deg, #ffffff, #f8fafc); 
                        padding: 2rem; border-radius: 16px; margin: 1rem 0; 
                        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);'>
            """, unsafe_allow_html=True)
            
            with st.form("register_form", clear_on_submit=False):
                st.markdown("### 👤 Informações Pessoais")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    first_name = st.text_input(
                        "👤 Nome", 
                        placeholder="Seu nome",
                        help="Digite seu primeiro nome"
                    )
                with col_b:
                    last_name = st.text_input(
                        "👤 Sobrenome", 
                        placeholder="Seu sobrenome",
                        help="Digite seu sobrenome"
                    )
                
                st.markdown("### 🔐 Dados de Acesso")
                
                username = st.text_input(
                    "👤 Nome de usuário", 
                    placeholder="Escolha um usuário único",
                    help="Este será seu nome de usuário para fazer login"
                )
                
                email = st.text_input(
                    "📧 E-mail", 
                    placeholder="seu@email.com",
                    help="Digite um e-mail válido"
                )
                
                phone = st.text_input(
                    "📱 Telefone (opcional)", 
                    placeholder="+55 11 99999-9999",
                    help="Telefone para contato (opcional)"
                )
                
                st.markdown("### 🔒 Senha")
                
                col_c, col_d = st.columns(2)
                with col_c:
                    password = st.text_input(
                        "🔑 Senha", 
                        type="password", 
                        placeholder="Digite uma senha segura",
                        help="Mínimo 6 caracteres"
                    )
                with col_d:
                    confirm_password = st.text_input(
                        "🔑 Confirmar senha", 
                        type="password", 
                        placeholder="Confirme sua senha",
                        help="Digite a mesma senha novamente"
                    )
                
                # Termos e condições
                st.markdown("---")
                terms_accepted = st.checkbox(
                    "✅ Aceito os termos de uso e política de privacidade",
                    help="Leia nossos termos antes de continuar"
                )
                
                register_btn = st.form_submit_button("✅ Criar Minha Conta", use_container_width=True, type="primary")
                
                if register_btn:
                    # Validações
                    if not all([first_name, last_name, username, email, password]):
                        st.error("❌ Preencha todos os campos obrigatórios!")
                    elif not terms_accepted:
                        st.error("❌ Você deve aceitar os termos de uso!")
                    elif password != confirm_password:
                        st.error("❌ As senhas não coincidem!")
                    elif len(password) < 6:
                        st.error("❌ A senha deve ter pelo menos 6 caracteres!")
                    else:
                        # Check if username/email already exists
                        if get_user_by_username(username):
                            st.error("❌ Nome de usuário já existe! Escolha outro.")
                        elif get_user_by_email(email):
                            st.error("❌ E-mail já cadastrado! Use outro e-mail.")
                        else:
                            try:
                                password_hash = hash_password(password)
                                user_id = create_user(username, email, password_hash, first_name, last_name, phone)
                                
                                if user_id:
                                    st.success("🎉 Conta criada com sucesso!")
                                    st.session_state.user_id = user_id
                                    st.session_state.username = username
                                    st.session_state.first_name = first_name
                                    st.session_state.role = "customer"
                                    
                                    # Transfer session cart if exists
                                    if 'session_cart' in st.session_state:
                                        for item in st.session_state.session_cart:
                                            add_to_cart(user_id, item['product_id'], item.get('quantity', 1))
                                        del st.session_state.session_cart
                                    
                                    if st.session_state.get('from_checkout', False):
                                        st.session_state.page = "checkout"
                                        st.session_state.pop('from_checkout', None)
                                    else:
                                        st.session_state.page = "home"
                                    
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao criar conta. Tente novamente.")
                            except Exception as e:
                                st.error(f"❌ Erro ao criar conta: {str(e)}")
            
            st.markdown("</div>", unsafe_allow_html=True)






def show_header():
    """Mostra cabeçalho da aplicação"""
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.markdown("""<h1 style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.5rem; margin: 0;">🛒 E-Store</h1>""", unsafe_allow_html=True)
    
    with col2:
        if 'user_id' in st.session_state:
            st.markdown(f"""<p style="text-align: center; margin: 0.5rem 0; color: #4b5563;">👋 Olá, {st.session_state.first_name}!</p>""", unsafe_allow_html=True)
        else:
            # Mostrar contador do carrinho mesmo sem login
            session_cart_items = st.session_state.get('session_cart', [])
            total_items = sum(item.get('quantity', 0) for item in session_cart_items)
            st.markdown(f"""<p style="text-align: center; color: #6b7280;">🛒 {total_items} itens</p>""", unsafe_allow_html=True)
    
    with col3:
        if 'user_id' in st.session_state:
            col_a, col_b = st.columns(2)
            with col_a:
                # Mostrar contador de itens no botão do carrinho
                session_cart_items = st.session_state.get('session_cart', [])
                total_items = sum(item.get('quantity', 0) for item in session_cart_items)
                cart_label = f"🛒 ({total_items})" if total_items > 0 else "🛒"
                
                if st.button(cart_label, use_container_width=True):
                    st.session_state.page = "cart"
                    st.rerun()
            with col_b:
                if st.button("🚪 Sair", use_container_width=True):
                    for key in ['user_id', 'username', 'role', 'first_name']:
                        st.session_state.pop(key, None)
                    st.session_state.page = "home"
                    st.rerun()
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                # Usuário não logado, mas pode ver o carrinho
                session_cart_items = st.session_state.get('session_cart', [])
                total_items = sum(item.get('quantity', 0) for item in session_cart_items)
                cart_label = f"🛒 ({total_items})" if total_items > 0 else "🛒"
                
                if st.button(cart_label, use_container_width=True):
                    st.session_state.page = "cart"
                    st.rerun()
            with col_b:
                if st.button("🔑 Login", use_container_width=True):
                    st.session_state.page = "login"
                    st.rerun()


def add_to_session_cart(product_id: int, quantity: int = 1):
    """Adiciona produto ao carrinho de sessão (sem login)"""
    if 'session_cart' not in st.session_state:
        st.session_state.session_cart = []
    
    # Verificar se produto já existe no carrinho
    for item in st.session_state.session_cart:
        if item['product_id'] == product_id:
            item['quantity'] += quantity
            return
    
    # Adicionar novo produto
    product = get_product_by_id(product_id)
    if product:
        st.session_state.session_cart.append({
            'product_id': product_id,
            'name': product['name'],
            'price': float(product['price']),
            'quantity': quantity,
            'image_url': product['image_url'] if product['image_url'] else ''
        })


def home_page():
    """Página inicial do e-commerce"""
    st.markdown("<h2 class='main-header'>🏪 Bem-vindo à E-Store</h2>", unsafe_allow_html=True)
    
    # Filtros com design melhorado
    st.markdown("<div style='background: linear-gradient(135deg, #f8fafc, #e2e8f0); padding: 1.5rem; border-radius: 16px; margin: 1rem 0;'>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        categories = get_all_categories()
        category_options = ["Todos"] + [cat['name'] for cat in categories]
        selected_category = st.selectbox("📂 Filtrar por Categoria", category_options, help="Filtrar produtos por categoria")
        
    with col2:
        search_query = st.text_input("🔍 Pesquisar produtos", 
                                    placeholder="Digite o nome do produto que procura...", 
                                    help="Encontre produtos por nome ou descrição")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Converter categoria para ID se necessário
    category_id = None
    if selected_category != "Todos":
        for cat in categories:
            if cat['name'] == selected_category:
                category_id = cat['id']
                break
    
    # Buscar produtos
    products = get_products_by_category(category_id, search_query if search_query else None)
    
    st.markdown("## 🛍️ Produtos Disponíveis")
    
    if not products:
        st.markdown("""
        <div style='text-align: center; padding: 3rem 1rem; color: #6b7280;'>
            <h1 style='font-size: 3rem; color: #d1d5db;'>🔍</h1>
            <h3>Nenhum produto encontrado</h3>
            <p>Tente ajustar os filtros ou fazer uma nova busca!</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Show products in grid with improved design
    st.markdown('<div class="product-grid">', unsafe_allow_html=True)
    
    # Create product grid with better columns
    n_products = len(products)
    grid_cols = 4 if n_products >= 4 else 3 if n_products >= 3 else 2
    
    cols = st.columns(grid_cols)
    for i, product in enumerate(products):
        with cols[i % grid_cols]:
            # Improved product card
            product_card = f"""
            <div class="product-card" style="text-align: center;">
                <img src="https://via.placeholder.com/250x200/667eea/white?text=Product" 
                     width="100%" style="border-radius: 8px; margin-bottom: 1rem;">
                <h4 style="color: #1f2937; margin: 0 0 0.5rem 0; font-size: 1.1rem;">{product['name']}</h4>
                <p style="color: #6b7280; font-size: 0.85rem; min-height: 2.5rem; line-height: 1.3;">
                    {product['description'][:60]}{'...' if len(product['description']) > 60 else ''}
                </p>
                <p style="font-size: 1.3rem; font-weight: 700; color: #059669; margin: 0.5rem 0;">
                    R$ {product['price']:,.2f}
                </p>
                <small style="color: #9ca3af;">📦 {product['stock']} em estoque</small>
            </div>
            """
            st.markdown(product_card, unsafe_allow_html=True)
            
            # Action buttons row
            button_col1, button_col2 = st.columns(2)
            
            with button_col1:
                if st.button("👁️ Ver", key=f"view_{product['id']}", use_container_width=True):
                    st.session_state.page = "product"
                    st.session_state.product_id = product['id']
                    st.rerun()
            
            with button_col2:
                if st.button("🛒+", key=f"cart_{product['id']}", use_container_width=True):
                    if product['stock'] > 0:
                        # Funciona sem login
                        add_to_session_cart(product['id'])
                        st.success("✅ Produto adicionado ao carrinho!")
                        st.rerun()
                    else:
                        st.error("❌ Produto fora de estoque!")
    
    st.markdown('</div>', unsafe_allow_html=True)


def product_detail_page():
    """Página de detalhes do produto"""
    product_id = st.session_state.get('product_id')
    if not product_id:
        st.error("❌ Produto não encontrado!")
        st.session_state.page = "home"
        st.rerun()
        return
    
    product = get_product_by_id(product_id)
    if not product:
        st.error("❌ Produto não encontrado!")
        st.session_state.page = "home"
        st.rerun()
        return
    
    # Botão voltar
    if st.button("← Voltar"):
        st.session_state.page = "home"
        st.rerun()
    
    st.markdown(f"## 📱 {product['name']}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Imagem do produto (placeholder)
        st.image("https://via.placeholder.com/400x300/3b82f6/white?text=Product+Image", 
                caption=product['name'], use_column_width=True)
    
    with col2:
        st.markdown(f"### 📝 Descrição")
        st.markdown(product['description'] or "Sem descrição disponível.")
        
        st.markdown(f"### 💰 Preço")
        st.markdown(f"""<p class="price-tag">R$ {product['price']:,.2f}</p>""", unsafe_allow_html=True)
        
        st.markdown(f"### 📦 Estoque")
        if product['stock'] > 0:
            st.success(f"✅ {product['stock']} disponível(is)")
        else:
            st.error("❌ Produto fora de estoque!")
        
        st.markdown("### 🛒 Ações")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            quantity = st.number_input("Quantidade", min_value=1, max_value=product['stock'], value=1)
        
        with col_b:
            if st.button("🛒 Adicionar ao Carrinho", use_container_width=True):
                if product['stock'] > 0:
                    # Works without login - add to session cart
                    if 'user_id' in st.session_state:
                        add_to_cart(st.session_state.user_id, product_id, quantity)
                    else:
                        for i in range(quantity):
                            add_to_session_cart(product_id)
                    st.success(f"✅ {quantity}x {product['name']} adicionado ao carrinho!")
                    st.rerun()
                else:
                    st.error("❌ Produto fora de estoque!")


def cart_page():
    """Página do carrinho"""
    st.markdown("## 🛒 Meu Carrinho")
    
    # Botão voltar
    if st.button("← Voltar"):
        st.session_state.page = "home"
        st.rerun()
    
    # Se usuário não está logado, usar carrinho de sessão
    if 'user_id' not in st.session_state:
        cart_items = st.session_state.get('session_cart', [])
    else:
        cart_items = get_cart_items(st.session_state.user_id)
    
    if not cart_items:
        st.markdown("""
        <div style='text-align: center; padding: 3rem 1rem; color: #6b7280;'>
            <h1 style='font-size: 4rem; color: #d1d5db;'>🛒</h1>
            <h2 style='margin: 0.5rem 0;'>Carrinho Vazio</h2>
            <p style='color: #9ca3af;'>Adicione produtos à seu carrinho!</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    total = 0
    
    for item in cart_items:
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        
        with col1:
            st.markdown(f"**{item['name']}**")
            st.markdown(f"R$ {item['price']:,.2f} cada")
        
        with col2:
            new_quantity = st.number_input("Qtd: ", min_value=0, value=item['quantity'], 
                                          key=f"qty_{item['id'] if 'id' in item else item['name']}")
            if new_quantity != item['quantity']:
                if 'user_id' not in st.session_state:
                    # Update session cart
                    for cart_item in st.session_state.session_cart:
                        if cart_item['product_id'] == item['product_id']:
                            if new_quantity == 0:
                                st.session_state.session_cart.remove(cart_item)
                            else:
                                cart_item['quantity'] = new_quantity
                            break
                    st.rerun()
                else:
                    # Update database cart
                    update_cart_item(st.session_state.user_id, item['product_id'], new_quantity)
                    st.rerun()
        
        with col3:
            subtotal = item['price'] * item['quantity']
            total += subtotal
            st.markdown(f"**R$ {subtotal:,.2f}**")
        
        with col4:
            st.text("")
        
        with col5:
            if st.button("🗑️", key=f"del_{item['id'] if 'id' in item else item['name']}", 
                        help="Remover"):
                if 'user_id' not in st.session_state:
                    # Remove from session cart
                    for cart_item in st.session_state.session_cart:
                        if cart_item['product_id'] == item['product_id']:
                            st.session_state.session_cart.remove(cart_item)
                            break
                    st.rerun()
                else:
                    # Remove from database cart
                    update_cart_item(st.session_state.user_id, item['product_id'], 0)
                    st.rerun()
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.markdown(f"## 💰 Total: **R$ {total:,.2f}**")
    
    with col2:
        # Finaliza compra direcionando para login se necessário
        if st.button("🛒 Finalizar Compra", use_container_width=True):
            if 'user_id' not in st.session_state:
                st.session_state.page = "login"
                st.session_state.from_checkout = True
                st.rerun()
            else:
                st.session_state.page = "checkout"
                st.rerun()
    
    with col3:
        if st.button("🗑️ Limpar Carrinho", use_container_width=True):
            if 'user_id' not in st.session_state:
                st.session_state.session_cart = []
                st.rerun()
            else:
                clear_cart(st.session_state.user_id)
                st.rerun()


def checkout_page():
    """Página de finalização da compra com sistema de pagamento integrado"""
    st.markdown("## 💳 Finalizar Compra")
    
    # Botão voltar
    if st.button("← Voltar"):
        st.session_state.page = "cart"
        st.rerun()
    
    if 'user_id' not in st.session_state:
        st.error("❌ Faça login para continuar!")
        return
    
    cart_items = get_cart_items(st.session_state.user_id)
    
    if not cart_items:
        st.info("🛒 Seu carrinho está vazio!")
        return
    
    # Calcular total
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    item_count = sum(item['quantity'] for item in cart_items)
    
    # Inicializar interface de pagamento
    payment_ui = PaymentUI()
    
    # Layout principal
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📋 Resumo do Pedido")
        
        # Mostrar itens do carrinho
        for item in cart_items:
            subtotal = item['price'] * item['quantity']
            st.markdown(f"**{item['name']}** x{item['quantity']} = R$ {subtotal:,.2f}")
        
        st.markdown("---")
        st.markdown(f"### 💰 **Total: R$ {total:,.2f}**")
        
        # Informações de entrega
        st.markdown("### 📝 Informações de Entrega")
        
        with st.form("shipping_form"):
            col_addr1, col_addr2 = st.columns([2, 1])
            
            with col_addr1:
                street = st.text_input(
                    "🏠 Rua/Avenida",
                    placeholder="Ex: Rua das Flores"
                )
                neighborhood = st.text_input(
                    "🏘️ Bairro",
                    placeholder="Ex: Centro"
                )
            
            with col_addr2:
                number = st.text_input(
                    "🔢 Número",
                    placeholder="123"
                )
                complement = st.text_input(
                    "🏢 Complemento",
                    placeholder="Apto 45 (opcional)"
                )
            
            col_city, col_state, col_cep = st.columns([2, 1, 1])
            
            with col_city:
                city = st.text_input(
                    "🏙️ Cidade",
                    placeholder="Ex: São Paulo"
                )
            
            with col_state:
                state = st.selectbox(
                    "🗺️ Estado",
                    ["", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", 
                     "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", 
                     "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
                )
            
            with col_cep:
                cep = st.text_input(
                    "📮 CEP",
                    placeholder="12345-678"
                )
            
            # Botão para confirmar endereço
            address_confirmed = st.form_submit_button("✅ Confirmar Endereço", use_container_width=True)
            
            # Montar endereço completo
            if address_confirmed and street and number and neighborhood and city and state and cep:
                complement_text = f", {complement}" if complement else ""
                shipping_address = f"{street}, {number}{complement_text} - {neighborhood} - {city} - {state} - CEP: {cep}"
                st.session_state.shipping_address = shipping_address
                st.success("✅ Endereço confirmado!")
            elif address_confirmed:
                st.error("❌ Por favor, preencha todos os campos obrigatórios!")
                shipping_address = None
            else:
                shipping_address = st.session_state.get('shipping_address', None)
        
        # Mostrar endereço confirmado
        if shipping_address:
            st.info(f"📍 **Endereço confirmado:** {shipping_address}")
    
    with col2:
        # Sistema de pagamento
        if shipping_address:
            order_data = {
                'total': total,
                'item_count': item_count,
                'order_id': f"TEMP_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'shipping_address': shipping_address
            }
            
            # Renderizar formulário de pagamento
            payment_result = payment_ui.render_payment_form(order_data)
            
            # Adicionar timestamp ao resultado do pagamento
            if payment_result and payment_result.get('status') in ['approved', 'pending']:
                st.session_state.payment_timestamp = time.time()
            
            # Processar resultado do pagamento
            if payment_result.get('status') == 'waiting':
                # Aguardando ação do usuário
                st.info("💡 Selecione uma forma de pagamento e preencha os dados para continuar.")
            elif payment_result.get('status') == 'approved':
                # Criar pedido no banco de dados
                order_id = create_order(
                    st.session_state.user_id,
                    cart_items,  # Passar os itens diretamente
                    shipping_address, 
                    payment_result.get('payment_method', 'PIX')
                )
                
                if order_id:
                    # Salvar transação de pagamento
                    create_payment_transaction(
                        order_id=order_id,
                        transaction_id=payment_result['transaction_id'],
                        payment_method=payment_result.get('payment_method', 'PIX'),
                        amount=total,
                        status=payment_result['status'],
                        gateway_response=json.dumps(payment_result.get('gateway_response', {})),
                        **{k: v for k, v in payment_result.items() 
                           if k in ['pix_key', 'pix_qr_code', 'boleto_number', 
                                   'boleto_barcode', 'boleto_due_date', 'card_last_four', 
                                   'card_brand', 'installments']}
                    )
                    
                    # Criar notificação
                    create_payment_notification(
                        transaction_id=payment_result['transaction_id'],
                        notification_type='payment_approved',
                        status='success',
                        message=f"Pagamento aprovado via {payment_result.get('payment_method', 'PIX')}"
                    )
                    
                    st.success("🎉 Pedido realizado com sucesso!")
                    st.balloons()
                    
                    # Limpar estado da sessão
                    if 'payment_result' in st.session_state:
                        del st.session_state.payment_result
                    if 'order_created' in st.session_state:
                        del st.session_state.order_created
                    
                    # Redirecionar para pedidos
                    st.session_state.page = "orders"
                    st.rerun()
                else:
                    st.error("❌ Erro ao processar pedido!")
            
            elif payment_result.get('status') == 'pending':
                # Para PIX e Boleto, criar o pedido mesmo com status pending
                if payment_result.get('payment_method') in ['PIX', 'Boleto Bancário']:
                    # Verificar se o pedido já foi criado
                    if 'order_created' not in st.session_state:
                        # Criar pedido no banco de dados
                        order_id = create_order(
                            st.session_state.user_id,
                            cart_items,  # Passar os itens diretamente
                            shipping_address, 
                            payment_result.get('payment_method', 'PIX')
                        )
                        
                        if order_id:
                            # Salvar transação de pagamento
                            create_payment_transaction(
                                order_id=order_id,
                                transaction_id=payment_result['transaction_id'],
                                payment_method=payment_result.get('payment_method', 'PIX'),
                                amount=total,
                                status=payment_result['status'],
                                gateway_response=json.dumps(payment_result.get('gateway_response', {})),
                                **{k: v for k, v in payment_result.items() 
                                   if k in ['pix_key', 'pix_qr_code', 'boleto_number', 
                                           'boleto_barcode', 'boleto_due_date', 'card_last_four', 
                                           'card_brand', 'installments']}
                            )
                            
                            # Marcar que o pedido foi criado
                            st.session_state.order_created = True
                            
                            st.success("🎉 Pedido criado com sucesso! Aguarde a confirmação do pagamento.")
                            
                            # Botão para ir aos pedidos
                            if st.button("📦 Ver Meus Pedidos", use_container_width=True, type="primary"):
                                # Limpar estado da sessão
                                if 'payment_result' in st.session_state:
                                    del st.session_state.payment_result
                                if 'order_created' in st.session_state:
                                    del st.session_state.order_created
                                
                                st.session_state.page = "orders"
                                st.rerun()
                            
                            # Mostrar instruções para PIX ou Boleto
                            if payment_result.get('payment_method') == 'PIX':
                                st.info("📱 **PIX Gerado!** Escaneie o QR Code ou use a chave PIX para pagar.")
                            elif payment_result.get('payment_method') == 'Boleto Bancário':
                                st.info("🏦 **Boleto Gerado!** Use o código de barras para pagar em qualquer banco ou lotérica.")
                        else:
                            st.error("❌ Erro ao processar pedido!")
                    else:
                        # Mostrar instruções para PIX ou Boleto
                        if payment_result.get('payment_method') == 'PIX':
                            st.info("📱 **PIX Gerado!** Escaneie o QR Code ou use a chave PIX para pagar.")
                        elif payment_result.get('payment_method') == 'Boleto Bancário':
                            st.info("🏦 **Boleto Gerado!** Use o código de barras para pagar em qualquer banco ou lotérica.")
        else:
            st.warning("⚠️ Preencha o endereço de entrega para continuar com o pagamento.")


def orders_page():
    """Página de pedidos do usuário"""
    if 'user_id' not in st.session_state:
        st.error("❌ Faça login para acessar seus pedidos!")
        return
    
    st.markdown("## 📦 Meus Pedidos")
    
    # Botão voltar
    if st.button("← Voltar"):
        st.session_state.page = "home"
        st.rerun()
    
    orders = get_user_orders(st.session_state.user_id)
    
    if not orders:
        st.info("📦 Você ainda não tem pedidos!")
        return
    
    for order in orders:
        status_display = get_status_display(order['status'])
        with st.expander(f"📋 Pedido {order['order_number']} - R$ {order['total_amount']:,.2f} - {status_display}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**📅 Data:** {datetime.fromtimestamp(order['created_at']).strftime('%d/%m/%Y %H:%M')}")
                st.markdown(f"**📍 Endereço:** {order['shipping_address']}")
                st.markdown(f"**💳 Pagamento:** {order['payment_method']}")
                st.markdown(f"**📊 Status:** {status_display}")
                
                # Mostrar itens do pedido
                order_details = get_order_details(order['id'])
                if order_details:
                    st.markdown("**🛍️ Produtos:**")
                    for item in order_details['items']:
                        st.markdown(f"- {item['quantity']}x {item['name']} - R$ {item['price']:,.2f}")
            
            with col2:
                # Mostrar informações de pagamento
                payments = get_order_payments(order['id'])
                if payments:
                    st.markdown("**💳 Informações de Pagamento:**")
                    for payment in payments:
                        status_color = {
                            'approved': '🟢',
                            'pending': '🟡', 
                            'failed': '🔴',
                            'cancelled': '⚫'
                        }.get(payment['status'], '⚪')
                        
                        st.markdown(f"{status_color} **{payment['payment_method']}**")
                        st.markdown(f"ID: `{payment['transaction_id']}`")
                        st.markdown(f"Status: {payment['status']}")
                        
                        # Mostrar dados específicos do método
                        if payment['payment_method'] == 'PIX' and payment['pix_key']:
                            st.markdown("**🔑 Chave PIX:**")
                            st.code(payment['pix_key'], language=None)
                            if payment['pix_qr_code']:
                                st.markdown("**📱 QR Code PIX:**")
                                st.image(payment['pix_qr_code'], width=200)
                            st.info("📱 **Como pagar:** Use a chave PIX ou escaneie o QR Code no seu app bancário.")
                            
                        elif payment['payment_method'] == 'Boleto Bancário' and payment['boleto_number']:
                            st.markdown("**📄 Dados do Boleto:**")
                            st.markdown(f"**Número:** {payment['boleto_number']}")
                            if payment['boleto_barcode']:
                                st.markdown("**Código de Barras:**")
                                st.code(payment['boleto_barcode'], language=None)
                            if payment['boleto_due_date']:
                                if isinstance(payment['boleto_due_date'], (int, float)):
                                    due_date = datetime.fromtimestamp(payment['boleto_due_date'])
                                else:
                                    due_date = payment['boleto_due_date']
                                st.markdown(f"**📅 Vencimento:** {due_date.strftime('%d/%m/%Y')}")
                            st.info("🏦 **Como pagar:** Vá a qualquer banco ou lotérica e informe o código de barras.")
                            
                        elif payment['payment_method'] == 'Cartão de Crédito' and payment['card_last_four']:
                            st.markdown(f"**💳 Cartão:** ****{payment['card_last_four']}")
                            if payment['card_brand']:
                                st.markdown(f"**Bandeira:** {payment['card_brand']}")
                            if payment['installments'] and payment['installments'] > 1:
                                st.markdown(f"**Parcelado em:** {payment['installments']}x")
                            else:
                                st.markdown("**💳 À Vista**")
                                
                        elif payment['payment_method'] == 'Cartão de Débito' and payment['card_last_four']:
                            st.markdown(f"**💳 Cartão:** ****{payment['card_last_four']}")
                            if payment['card_brand']:
                                st.markdown(f"**Bandeira:** {payment['card_brand']}")
                            st.markdown("**💳 À Vista** - Débito imediato")
                        
                        # Botão para imprimir boleto se for boleto
                        if payment['payment_method'] == 'Boleto Bancário' and payment['boleto_number']:
                            if st.button("🖨️ Imprimir Boleto", key=f"print_boleto_{payment['transaction_id']}", use_container_width=True):
                                st.success("✅ Boleto enviado para impressão!")
                        
                        # Botão para copiar chave PIX se for PIX
                        if payment['payment_method'] == 'PIX' and payment['pix_key']:
                            if st.button("📋 Copiar Chave PIX", key=f"copy_pix_{payment['transaction_id']}", use_container_width=True):
                                st.success("✅ Chave PIX copiada para a área de transferência!")
                        
                        st.markdown("---")
                else:
                    st.info("💳 Nenhuma informação de pagamento disponível.")


def safe_get(row_dict, key, default=""):
    """Helper function to safely get values from sqlite3.Row objects"""
    try:
        value = row_dict[key]
        return value if value is not None else default
    except (KeyError, TypeError):
        return default


def get_orders_summary():
    """Obter estatísticas dos pedidos"""
    orders = get_all_orders()
    
    if not orders:
        return {
            'total_orders': 0,
            'approved_orders': 0,
            'pending_orders': 0,
            'total_revenue': 0,
            'approved_revenue': 0
        }
    
    all_statuses = [order['status'] for order in orders]
    pending_orders = len([o for o in orders if o['status'] == 'pending'])
    approved_orders = len([o for o in orders if o['status'] in ['processing', 'shipped', 'delivered']])
    
    total_revenue = sum(order['total_amount'] for order in orders)
    approved_revenue = sum(order['total_amount'] for order in orders if order['status'] in ['processing', 'shipped', 'delivered'])
    
    return {
        'total_orders': len(orders),
        'approved_orders': approved_orders,
        'pending_orders': pending_orders,
        'total_revenue': total_revenue,
        'approved_revenue': approved_revenue
    }


def admin_dashboard():
    """Dashboard administrativo completo"""
    if 'user_id' not in st.session_state or st.session_state.get('role') != 'admin':
        st.error("❌ Acesso negado! Apenas administradores podem acessar esta área.")
        return
    
    # Header administrativo melhorado
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 12px; margin-bottom: 2rem; color: white;'>
        <h1 style='color: white; margin: 0;'>👨‍💼 Painel Administrativo</h1>
        <p style='color: #e5e7eb; margin: 0;'>Gerencie seus produtos, pedidos e vendas</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Obter estatísticas
    stats = get_orders_summary()
    
    with st.container():
        # Métricas principais em cards
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #10b981, #059669); padding: 1.5rem; border-radius: 12px; text-align: center; color: white;'>
                <h2 style='margin: 0; font-size: 2rem;'>{stats['total_orders']}</h2>
                <p style='margin: 0;'>Total de Pedidos</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 1.5rem; border-radius: 12px; text-align: center; color: white;'>
                <h2 style='margin: 0; font-size: 2rem;'>{stats['approved_orders']}</h2>
                <p style='margin: 0;'>Pedidos Aprovados</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #f59e0b, #d97706); padding: 1.5rem; border-radius: 12px; text-align: center; color: white;'>
                <h2 style='margin: 0; font-size: 2rem;'>{stats['pending_orders']}</h2>
                <p style='margin: 0;'>Pagamentos Pendentes</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #8b5cf6, #7c3aed); padding: 1.5rem; border-radius: 12px; text-align: center; color: white;'>
                <h2 style='margin: 0; font-size: 1.5rem;'>R$ {stats['approved_revenue']:,.0f}</h2>
                <p style='margin: 0;'>Receita dos Pagos</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #ec4899, #db2777); padding: 1.5rem; border-radius: 12px; text-align: center; color: white;'>
                <h2 style='margin: 0; font-size: 1.5rem;'>R$ {stats['total_revenue']:,.0f}</h2>
                <p style='margin: 0;'>Total de Receita</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("") # Espaço
    
    # Tabs para funcionalidades
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(["📦 Produtos", "📋 Pedidos", "💳 Pagamentos", "⚙️ Config Pagamentos", "🔍 Monitor", "🧾 Notas Fiscais", "📈 Vendas", "🔧 Cadastro", "👥 Usuários"])
    
    with tab1:
        st.markdown("### 📦 Gestão de Produtos")
        
        # Lista de produtos existentes
        products = get_products_by_category()
        
        for product in products:
            with st.expander(f"📱 {product['name']} - R$ {float(product['price']):,.2f}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**📝 Descrição:** {product['description']}")
                    st.markdown(f"**📦 Estoque:** {product['stock']}")
                    st.markdown(f"**🏷️ Categoria:** {safe_get(product, 'category_name', 'N/A')}")
                    if product['image_url']:
                        st.markdown(f"**🖼️ Imagem:** {product['image_url']}")
                    else:
                        st.warning("⚠️ Produto sem imagem")
                
                with col2:
                    st.number_input("Estoque atual:", value=product['stock'], min_value=0, 
                                   key=f"stock_display_{product['id']}")
                    st.info("💡 Use o botão '🔧 Editar Produto' abaixo para editar este produto")
        
        # Criar novo produto
        st.markdown("### ➕ Cadastrar Novo Produto")
        with st.form("new_product"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Nome do produto")
                description = st.text_area("Descrição")
            with col2:
                price = st.number_input("Preço (R$)", min_value=0.0, step=0.01)
                stock = st.number_input("Estoque", min_value=0, step=1)
            
            categories = get_all_categories()
            category_id = st.selectbox("Categoria", options=[c['id'] for c in categories], 
                                     format_func=lambda x: next(c['name'] for c in categories if c['id'] == x))
            
            image_url = st.text_input("URL da imagem", placeholder="https://example.com/image.jpg")
            
            submitted = st.form_submit_button("✅ Cadastrar Produto")
            if submitted:
                if name and description and price and stock is not None:
                    # Aqui vocẽ poderia adicionar a função para criar novo produto
                    st.success("✅ Novo produto cadastrado com sucesso!")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios!")
    
    with tab2:
        st.markdown("### 📋 Gestão de Pedidos")
        orders = get_all_orders()
        
        if not orders:
            st.info("📭 Nenhum pedido encontrado")
        else:
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox("Filtrar por status", 
                                           ["Todos"] + list(set(order['status'] for order in orders)))
            with col2:
                search_order = st.text_input("Pesquisar pedido", placeholder="Número do pedido...")
            
            # Lista de pedidos
            for order in orders:
                if status_filter != "Todos" and order['status'] != status_filter:
                    continue
                
                status_display = get_status_display(order['status'])
                with st.expander(f"📦 {order['order_number']} - {order['first_name']} {order['last_name']} - Status: {status_display}"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**💰 Total:** R$ {float(order['total_amount']):,.2f}")
                        st.markdown(f"**📍 Endereço:** {order['shipping_address']}")
                        st.markdown(f"**💳 Pagamento:** {order['payment_method']}")
                        st.markdown(f"**📅 Data:** {datetime.fromtimestamp(order['created_at']).strftime('%d/%m/%Y %H:%M')}")
                    
                    with col2:
                        available_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
                        current_index = available_statuses.index(order['status']) if order['status'] in available_statuses else 0
                        new_status = st.selectbox("Status", available_statuses, 
                                                index=current_index, key=f"status_{order['id']}")
                    
                    with col3:
                        if st.button("✅ Atualizar", key=f"update_{order['id']}"):
                            # Usar a função correta para atualizar status
                            success = update_order_status(order['id'], new_status)
                            if success:
                                st.success(f"✅ Status atualizado para: {new_status}")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao atualizar status!")
                    
                    # Mostrar itens do pedido
                    order_details = get_order_details(order['id'])
                    if order_details:
                        st.markdown("**🛍️ Itens do pedido:**")
                        for item in order_details['items']:
                            st.markdown(f"- {item['quantity']}x {item['name']} - R$ {float(item['price']):,.2f}")
    
    with tab3:
        st.markdown("### 💳 Gestão de Pagamentos")
        
        # Filtros para pagamentos
        col1, col2, col3 = st.columns(3)
        with col1:
            payment_status_filter = st.selectbox("Filtrar por status", 
                                               ["Todos", "approved", "pending", "failed", "cancelled"])
        with col2:
            payment_method_filter = st.selectbox("Filtrar por método", 
                                               ["Todos", "PIX", "Cartão de Crédito", "Cartão de Débito", "Boleto Bancário"])
        with col3:
            search_transaction = st.text_input("Pesquisar transação", placeholder="ID da transação...")
        
        # Obter todas as transações
        conn = get_conn()
        cur = conn.cursor()
        
        query = """
            SELECT pt.*, o.order_number, o.total_amount, u.first_name, u.last_name
            FROM payment_transactions pt
            JOIN orders o ON pt.order_id = o.id
            JOIN users u ON o.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if payment_status_filter != "Todos":
            query += " AND pt.status = ?"
            params.append(payment_status_filter)
        
        if payment_method_filter != "Todos":
            query += " AND pt.payment_method = ?"
            params.append(payment_method_filter)
        
        if search_transaction:
            query += " AND pt.transaction_id LIKE ?"
            params.append(f"%{search_transaction}%")
        
        query += " ORDER BY pt.created_at DESC"
        
        cur.execute(query, params)
        transactions = cur.fetchall()
        conn.close()
        
        if not transactions:
            st.info("💳 Nenhuma transação encontrada")
        else:
            # Métricas de pagamento
            col1, col2, col3, col4 = st.columns(4)
            
            total_transactions = len(transactions)
            approved_transactions = len([t for t in transactions if t['status'] == 'approved'])
            pending_transactions = len([t for t in transactions if t['status'] == 'pending'])
            total_revenue = sum(float(t['amount']) for t in transactions if t['status'] == 'approved')
            
            with col1:
                st.metric("Total de Transações", total_transactions)
            with col2:
                st.metric("Pagamentos Aprovados", approved_transactions)
            with col3:
                st.metric("Pagamentos Pendentes", pending_transactions)
            with col4:
                st.metric("Receita Total", f"R$ {total_revenue:,.2f}")
            
            st.markdown("---")
            
            # Lista de transações
            for transaction in transactions:
                with st.expander(f"💳 {transaction['transaction_id']} - {transaction['payment_method']} - R$ {float(transaction['amount']):,.2f}"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**👤 Cliente:** {transaction['first_name']} {transaction['last_name']}")
                        st.markdown(f"**📋 Pedido:** {transaction['order_number']}")
                        st.markdown(f"**💰 Valor:** R$ {float(transaction['amount']):,.2f}")
                        st.markdown(f"**📅 Data:** {datetime.fromtimestamp(transaction['created_at']).strftime('%d/%m/%Y %H:%M')}")
                        
                        # Mostrar dados específicos do método
                        if transaction['payment_method'] == 'PIX' and transaction['pix_key']:
                            st.markdown(f"**🔑 Chave PIX:** `{transaction['pix_key']}`")
                        elif transaction['payment_method'] == 'Boleto Bancário' and transaction['boleto_number']:
                            st.markdown(f"**📄 Boleto:** `{transaction['boleto_number']}`")
                            if transaction['boleto_due_date']:
                                due_date = datetime.fromtimestamp(transaction['boleto_due_date'])
                                st.markdown(f"**📅 Vencimento:** {due_date.strftime('%d/%m/%Y')}")
                        elif transaction['payment_method'] == 'Cartão de Crédito':
                            if transaction['card_last_four']:
                                st.markdown(f"**💳 Cartão:** ****{transaction['card_last_four']}")
                            if transaction['installments'] and transaction['installments'] > 1:
                                st.markdown(f"**📊 Parcelas:** {transaction['installments']}x")
                        elif transaction['payment_method'] == 'Cartão de Débito':
                            if transaction['card_last_four']:
                                st.markdown(f"**💳 Cartão:** ****{transaction['card_last_four']}")
                            st.markdown("**💰 Tipo:** À Vista - Débito Imediato")
                    
                    with col2:
                        # Status atual
                        status_colors = {
                            'approved': '🟢 Aprovado',
                            'pending': '🟡 Pendente',
                            'failed': '🔴 Falhou',
                            'cancelled': '⚫ Cancelado'
                        }
                        current_status = status_colors.get(transaction['status'], f"⚪ {transaction['status']}")
                        st.markdown(f"**Status:** {current_status}")
                        
                        # Gateway response se disponível
                        if transaction['gateway_response']:
                            try:
                                gateway_data = json.loads(transaction['gateway_response'])
                                if 'authorization_code' in gateway_data:
                                    st.markdown(f"**Código:** `{gateway_data['authorization_code']}`")
                            except:
                                pass
                    
                    with col3:
                        # Ações administrativas
                        if transaction['status'] == 'pending':
                            if st.button("✅ Aprovar", key=f"approve_{transaction['id']}"):
                                success = update_payment_status(transaction['transaction_id'], 'approved')
                                if success:
                                    st.success("✅ Pagamento aprovado!")
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao aprovar pagamento!")
                        
                        if transaction['status'] in ['pending', 'approved']:
                            if st.button("❌ Cancelar", key=f"cancel_{transaction['id']}"):
                                success = update_payment_status(transaction['transaction_id'], 'cancelled')
                                if success:
                                    st.success("✅ Pagamento cancelado!")
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao cancelar pagamento!")
                        
                        # Ver notificações
                        notifications = get_payment_notifications(transaction['transaction_id'])
                        if notifications:
                            st.markdown(f"**📧 Notificações:** {len(notifications)}")
    
    with tab4:
        # Página de configuração de pagamentos
        try:
            from payment_config import render_payment_config_page
            render_payment_config_page()
        except ImportError:
            st.error("❌ Módulo de configuração de pagamentos não encontrado!")
            st.info("📝 Certifique-se de que o arquivo payment_config.py está presente.")
    
    with tab5:
        # Página de monitoramento de pagamentos
        try:
            from payment_monitor import render_payment_monitor_page
            render_payment_monitor_page()
        except ImportError:
            st.error("❌ Módulo de monitoramento de pagamentos não encontrado!")
            st.info("📝 Certifique-se de que o arquivo payment_monitor.py está presente.")
    
    with tab6:
        # Sistema de Notas Fiscais
        try:
            from invoice_system import render_invoice_system
            render_invoice_system()
        except ImportError:
            st.error("❌ Módulo de notas fiscais não encontrado!")
            st.info("📝 Certifique-se de que o arquivo invoice_system.py está presente.")
    
    with tab7:
        st.markdown("### 📈 Relatórios de Vendas")
        
        # Gráfico de vendas
        if orders and PLOTLY_AVAILABLE:
            df = pd.DataFrame([{
                'Data': datetime.fromtimestamp(order['created_at']).strftime('%d/%m'),
                'Receita': float(order['total_amount'])
            } for order in orders])
            
            daily_sales = df.groupby('Data')['Receita'].sum().reset_index()
            
            if not daily_sales.empty:
                fig = px.line(daily_sales, x='Data', y='Receita', title="📈 Vendas Diárias", 
                            color_discrete_sequence=['#667eea'])
                st.plotly_chart(fig, use_container_width=True)
        
        # Tabela de resumo
        if orders:
            df_orders = pd.DataFrame([{
                'Data': datetime.fromtimestamp(order['created_at']).strftime('%d/%m/%Y'),
                'Status': order['status'].title(),
                'Total (R$)': f"R$ {float(order['total_amount']):,.2f}"
            } for order in orders])
            st.dataframe(df_orders, use_container_width=True)
    
    with tab4:
        st.markdown("### 🔧 Cadastro de Produtos")
        
        # Página de cadastro de produtos com upload de imagem
        st.markdown("#### ➕ Adicionar Novo Produto")
        
        with st.form("new_product_form"):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                product_name = st.text_input("🎯 Nome do Produto", placeholder="Nome do produto...")
                product_description = st.text_area("📝 Descrição", placeholder="Descrição detalhada do produto...")
                price = st.number_input("💰 Preço (R$)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
                stock = st.number_input("📦 Quantidade em Estoque", min_value=0, value=0, step=1)
                
            with col2:
                # Seletor de categoria
                categories = get_all_categories()
                category_options = {c['id']: c['name'] for c in categories}
                category_selection = st.selectbox("🏷️ Categoria", 
                                                 options=list(category_options.keys()),
                                                 format_func=lambda x: category_options[x])
                
                # Upload de imagem
                uploaded_image = st.file_uploader("🖼️ Foto do Produto", 
                                               type=['jpg', 'jpeg', 'png', 'gif'],
                                               help="Carregue uma imagem para o produto")
                
                # URL de imagem alternativa
                image_url_alt = st.text_input("🔗 URL da Imagem", 
                                            placeholder="https://example.com/image.jpg",
                                            help="Ou forneça URL direta da imagem")
            
            # SKU 
            sku_field = st.text_input("🏷️ SKU (Código)", placeholder="Código único do produto...")
            
            submit_b = st.form_submit_button("✅ Criar Produto", use_container_width=True)
            
            if submit_b:
                # Validação
                if not product_name or not product_description or price == 0:
                    st.error("❌ Preencha os campos obrigatórios: Nome, descrição e preço!")
                else:
                    # Determinar fonte da imagem
                    image_source = ""
                    if uploaded_image is not None:
                        # Processar imagem carregada
                        image_bytes = uploaded_image.read()
                        image_base64 = base64.b64encode(image_bytes).decode()
                        image_source = f"data:{uploaded_image.type};base64,{image_base64}"
                    elif image_url_alt:
                        image_source = image_url_alt
                    else:
                        # Usar placeholder default
                        image_source = "https://via.placeholder.com/300x300/e5e7eb/6b7280?text=Produto"
                    
                    # Criar produto
                    try:
                        product_id = create_product(
                            name=product_name,
                            description=product_description, 
                            price=float(price),
                            stock=int(stock),
                            category_id=int(category_selection),
                            image_url=image_source,
                            sku=sku_field if sku_field else None
                        )
                        
                        if product_id:
                            st.success("✅ Produto cadastrado com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao cadastrar produto!")
                    except Exception as e:
                        st.error(f"❌ Erro ao cadastrar produto: {str(e)}")
        
        st.markdown("---")
        
        # Verificar se há um produto sendo editado
        if 'edit_product_id' in st.session_state and st.session_state.edit_product_id:
            edit_product_id = st.session_state.edit_product_id
            product_to_edit = get_product_by_id(edit_product_id)
            
            if product_to_edit:
                st.markdown("#### ✏️ Editando Produto")
                
                # Botão para cancelar edição
                if st.button("❌ Cancelar Edição"):
                    st.session_state.pop('edit_product_id', None)
                    st.rerun()
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Exibir imagem atual
                    image_url = product_to_edit['image_url'] if product_to_edit['image_url'] else None
                    if image_url:
                        st.image(image_url, width=200, caption="Imagem atual")
                    else:
                        st.warning("⚠️ Produto sem imagem")
                    
                    # Formulário de edição
                    st.markdown("**📝 Editar informações:**")
                    
                    edit_name = st.text_input("Nome", value=product_to_edit['name'], key="edit_name_current")
                    edit_desc = st.text_area("Descrição", value=product_to_edit['description'], key="edit_desc_current")
                    edit_price = st.number_input("Preço", value=float(product_to_edit['price']), min_value=0.0, step=0.01, key="edit_price_current")
                    edit_stock = st.number_input("Estoque", value=int(product_to_edit['stock']), min_value=0, step=1, key="edit_stock_current")
                    
                with col2:
                    # Novo upload de imagem
                    st.markdown("**🖼️ Atualizar imagem:**")
                    new_image = st.file_uploader("Nova foto", 
                                               type=['jpg', 'jpeg', 'png'],
                                               key="new_image_current")
                    
                    new_image_url = st.text_input("URL nova imagem", 
                                                key="new_url_current",
                                                placeholder="https://...")
                    
                    # Botões de ação
                    action_col1, action_col2 = st.columns(2)
                    
                    with action_col1:
                        save_btn = st.button("💾 Salvar Alterações", key="save_current", type="primary")
                    with action_col2:
                        remove_btn = st.button("🗑️ Remover Produto", key="remove_current")
                    
                    st.markdown(f"**ID do Produto:** {product_to_edit['id']}")
                    
                    if save_btn:
                        try:
                            updates = {}
                            
                            # Verificar mudanças nos campos
                            if edit_name and edit_name.strip() != product_to_edit['name']:
                                updates['name'] = edit_name.strip()
                            if edit_desc and edit_desc.strip() != product_to_edit['description']:
                                updates['description'] = edit_desc.strip()
                            if edit_price is not None and float(edit_price) != float(product_to_edit['price']):
                                updates['price'] = float(edit_price)
                            if edit_stock is not None and int(edit_stock) != int(product_to_edit['stock']):
                                updates['stock'] = int(edit_stock)
                            
                            # Processar imagem
                            image_to_use = None
                            if new_image:
                                # Processar nova imagem carregada
                                image_bytes = new_image.read()
                                image_base64 = base64.b64encode(image_bytes).decode() 
                                image_to_use = f"data:{new_image.type};base64,{image_base64}"
                            elif new_image_url and new_image_url.strip():
                                # Usar URL fornecida
                                image_to_use = new_image_url.strip()
                            
                            if image_to_use is not None:
                                updates['image_url'] = image_to_use
                            
                            # Executar atualização se houver mudanças
                            if updates:
                                success = update_product(product_to_edit['id'], **updates)
                                if success:
                                    st.success("✅ Produto atualizado com sucesso!")
                                    st.session_state.pop('edit_product_id', None)
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao atualizar produto!")
                            else:
                                st.info("ℹ️ Nenhuma alteração detectada.")
                                
                        except Exception as e:
                            st.error(f"❌ Erro ao processar atualização: {str(e)}")
                    
                    if remove_btn:
                        confirm_delete = st.session_state.get("confirm_delete_current", False)
                        if not confirm_delete:
                            st.session_state["confirm_delete_current"] = True
                            st.warning("⚠️ Clique novamente para confirmar remoção!")
                        else:
                            delete_product(product_to_edit['id'])
                            st.success("✅ Produto removido!")
                            st.session_state.pop("confirm_delete_current", None)
                            st.session_state.pop('edit_product_id', None)
                            st.rerun()
            else:
                st.error("❌ Produto não encontrado!")
                st.session_state.pop('edit_product_id', None)
                st.rerun()
        
        # Modal de confirmação de exclusão
        if st.session_state.get('show_delete_confirmation', False):
            delete_product_id = st.session_state.get('delete_product_id')
            product_to_delete = get_product_by_id(delete_product_id)
            
            if product_to_delete:
                st.markdown("---")
                st.markdown("### ⚠️ Confirmar Exclusão")
                st.warning(f"**Você tem certeza que deseja excluir o produto '{product_to_delete['name']}'?**")
                st.info("💡 **Importante:** Se houver pedidos ativos com este produto, ele será apenas desativado. Caso contrário, será excluído permanentemente.")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if st.button("✅ Sim, Excluir", type="primary", use_container_width=True):
                        if delete_product(delete_product_id):
                            st.success("✅ Produto excluído com sucesso!")
                            st.session_state.pop('delete_product_id', None)
                            st.session_state.pop('show_delete_confirmation', None)
                            st.rerun()
                        else:
                            st.error("❌ Erro ao excluir produto!")
                
                with col2:
                    if st.button("❌ Cancelar", use_container_width=True):
                        st.session_state.pop('delete_product_id', None)
                        st.session_state.pop('show_delete_confirmation', None)
                        st.rerun()
                
                st.markdown("---")
            else:
                st.error("❌ Produto não encontrado!")
                st.session_state.pop('delete_product_id', None)
                st.session_state.pop('show_delete_confirmation', None)
                st.rerun()
        
        # Lista de produtos com opções de edição
        st.markdown("#### 📦 Produtos Existentes")
        all_products = get_products_by_category()
        
        if not all_products:
            st.warning("⚠️ Nenhum produto encontrado no banco de dados!")
        else:
            st.success(f"✅ {len(all_products)} produtos encontrados!")
        
        for product in all_products:
            with st.expander(f"📱 {product['name']} - R$ {float(product['price']):,.2f} | Estoque: {product['stock']}"):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Exibir informações do produto
                    st.markdown(f"**📝 Descrição:** {product['description']}")
                    st.markdown(f"**📦 Estoque:** {product['stock']}")
                    st.markdown(f"**🏷️ Categoria:** {product['category_name'] if 'category_name' in product.keys() else 'N/A'}")
                    
                    # Exibir imagem atual
                    image_url = product['image_url'] if product['image_url'] else None
                    if image_url:
                        st.image(image_url, width=200, caption="Imagem atual")
                    else:
                        st.warning("⚠️ Produto sem imagem")
                
                with col2:
                    st.markdown("**⚙️ Ações:**")
                    
                    # Botões de ação - mais visíveis
                    st.markdown("---")
                    
                    # Botão Editar
                    if st.button("🔧 Editar Produto", key=f"edit_{product['id']}", use_container_width=True, type="primary"):
                        st.session_state.edit_product_id = product['id']
                        st.rerun()
                    
                    # Botão Excluir
                    if st.button("🗑️ Excluir Produto", key=f"delete_{product['id']}", use_container_width=True, type="secondary"):
                        st.session_state.delete_product_id = product['id']
                        st.session_state.show_delete_confirmation = True
                        st.rerun()
                    
                    st.markdown("---")
                    
                    # Campo para ajustar estoque rapidamente
                    st.markdown("**📦 Ajuste Rápido de Estoque:**")
                    new_stock = st.number_input(
                        "Estoque atual:", 
                        value=product['stock'], 
                        min_value=0, 
                        key=f"stock_{product['id']}"
                    )
                    
                    if new_stock != product['stock']:
                        if st.button("💾 Atualizar Estoque", key=f"update_stock_{product['id']}"):
                            success = update_product(product['id'], stock=new_stock)
                            if success:
                                st.success("✅ Estoque atualizado!")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao atualizar estoque!")
                    
                    st.markdown(f"**ID:** {product['id']}")
    
    with tab5:
        st.markdown("### 👥 Gestão de Usuários")
        # Aqui você implementaria a gestão de usuários
        st.info("👥 Funcionalidades de gestão de usuários serão implementadas aqui")
        
        st.markdown("---")
        st.markdown("### ⚙️ Configurações do Sistema")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 Limpar Cache do Sistema", use_container_width=True):
                st.cache_data.clear()
                if 'payment_result' in st.session_state:
                    del st.session_state.payment_result
                if 'payment_timestamp' in st.session_state:
                    del st.session_state.payment_timestamp
                st.session_state.last_cache_clear = time.time()
                st.success("✅ Cache limpo com sucesso!")
                st.rerun()
        
        with col2:
            if st.button("🔄 Recarregar Aplicação", use_container_width=True):
                st.rerun()
        
        # Informações do sistema
        st.markdown("#### 📊 Informações do Sistema")
        last_clear = st.session_state.get('last_cache_clear', 0)
        if last_clear > 0:
            last_clear_time = datetime.fromtimestamp(last_clear).strftime('%d/%m/%Y %H:%M:%S')
            st.info(f"🕒 Última limpeza de cache: {last_clear_time}")
        else:
            st.info("🕒 Cache ainda não foi limpo nesta sessão")


def main():
    """Função principal da aplicação"""
    
    # Limpeza automática de cache
    auto_clear_cache()
    
    # Inicializar banco
    init_db()
    
    # Inicializar estado da sessão
    if 'page' not in st.session_state:
        st.session_state.page = "home"
    
    if 'show_register' not in st.session_state:
        st.session_state.show_register = False
    
    # Header
    show_header()
    
    # Sidebar para navegação (apenas se logado)
    if 'user_id' in st.session_state:
        with st.sidebar:
            st.markdown("### 🧭 Navegação")
            
            pages = {
                "🏠 Início": "home",
                "🛍️ Produtos": "home",
                "🛒 Carrinho": "cart",
                "📦 Meus Pedidos": "orders"
            }
            
            # Adicionar páginas do admin
            if st.session_state.get('role') == 'admin':
                pages["👨‍💼 Admin"] = "admin"
            
            for page_name, page_key in pages.items():
                if st.button(page_name, use_container_width=True):
                    st.session_state.page = page_key
                    st.rerun()
    
    
    # Renderizar página atual
    current_page = st.session_state.get('page', 'home')
    
    if current_page == "home":
        home_page()
    elif current_page == "product":
        product_detail_page()
    elif current_page == "cart":
        cart_page()
    elif current_page == "checkout":
        checkout_page()
    elif current_page == "orders":
        orders_page()
    elif current_page == "login":
        login_page()
    elif current_page == "admin":
        admin_dashboard()


if __name__ == "__main__":
    main()
