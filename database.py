import os
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
# import streamlit as st  # Comentado para evitar problemas de importação
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "ecommerce.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'customer',
            status TEXT NOT NULL DEFAULT 'active',
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        )
    """)

    # Categories table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            image_url TEXT,
            parent_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            FOREIGN KEY(parent_id) REFERENCES categories(id)
        )
    """)

    # Products table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            category_id INTEGER,
            image_url TEXT,
            sku TEXT UNIQUE,
            is_active BOOLEAN DEFAULT 1,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            updated_at INTEGER DEFAULT (strftime('%s','now')),
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    """)

    # Cart table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id),
            UNIQUE(user_id, product_id)
        )
    """)

    # Orders table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_number TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            total_amount DECIMAL(10,2) NOT NULL,
            shipping_address TEXT,
            billing_address TEXT,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'pending',
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            updated_at INTEGER DEFAULT (strftime('%s','now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Order items table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    # Payment transactions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            transaction_id TEXT UNIQUE NOT NULL,
            payment_method TEXT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            gateway_response TEXT,
            pix_key TEXT,
            pix_qr_code TEXT,
            boleto_number TEXT,
            boleto_barcode TEXT,
            boleto_due_date INTEGER,
            card_last_four TEXT,
            card_brand TEXT,
            installments INTEGER DEFAULT 1,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            updated_at INTEGER DEFAULT (strftime('%s','now')),
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    """)

    # Payment notifications table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            processed_at INTEGER,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            FOREIGN KEY(transaction_id) REFERENCES payment_transactions(transaction_id)
        )
    """)

    # Payment methods configuration table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_methods_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method_name TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            processing_fee DECIMAL(5,2) DEFAULT 0.00,
            min_amount DECIMAL(10,2) DEFAULT 0.00,
            max_amount DECIMAL(10,2) DEFAULT 999999.99,
            config_data TEXT,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        )
    """)

    # Invoices table (Notas Fiscais)
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

    conn.commit()
    conn.close()


def seed_initial_data() -> None:
    conn = get_conn()
    cur = conn.cursor()

    # Check if admin user exists
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = cur.fetchone()[0]
    
    if admin_count == 0:
        # Create default admin
        import bcrypt
        admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
        cur.execute("""
            INSERT INTO users (username, email, password_hash, first_name, last_name, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("admin", "admin@ecommerce.com", admin_password, "Admin", "System", "admin"))

    # Check if categories exist
    cur.execute("SELECT COUNT(*) FROM categories")
    cat_count = cur.fetchone()[0]
    
    if cat_count == 0:
        # Insert default categories
        categories = [
            ("Eletrônicos", "Produtos eletrônicos em geral"),
            ("Roupas", "Vestuário masculino e feminino"),
            ("Casa e Jardim", "Itens para casa e jardim"),
            ("Livros", "Livros e materiais educativos"),
            ("Esportes", "Artigos esportivos")
        ]
        
        for name, desc in categories:
            cur.execute("""
                INSERT INTO categories (name, description)
                VALUES (?, ?)
            """, (name, desc))

    # Check if products exist
    cur.execute("SELECT COUNT(*) FROM products")
    prod_count = cur.fetchone()[0]
    
    if prod_count == 0:
        # Insert default products
        products = [
            ("Smartphone Galaxy S23", "O mais novo smartphone com o melhor custo-benefício", 899.99, 50, 1, "smartphone-01"),
            ("Notebook Dell Inspiron", "Notebook para uso doméstico e profissional", 2499.99, 25, 1, "notebook-01"),
            ("Camiseta Premium", "Camiseta 100% algodão", 49.99, 100, 2, "camiseta-01"),
            ("Tênis Esportivo", "Tênis para corrida e caminhada", 299.99, 75, 5, "tenis-01"),
            ("Smart Watch", "Relógio inteligente com GPS", 599.99, 30, 1, "smartwatch-01"),
            ("Livro Python", "Aprenda Python do zero", 89.99, 200, 4, "livro-01")
        ]
        
        for name, desc, price, stock, category, sku in products:
            cur.execute("""
                INSERT INTO products (name, description, price, stock, category_id, sku)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, desc, price, stock, category, sku))

    # Seed payment methods
    seed_payment_methods()
    
    conn.commit()
    conn.close()


# User functions
def create_user(username: str, email: str, password_hash: bytes, first_name: str, last_name: str, phone: str = None) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, email, password_hash, first_name, last_name, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, email, password_hash, first_name, last_name, phone))
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    conn.close()
    return user


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user


def authenticate_user(username: str, password: str) -> Optional[sqlite3.Row]:
    user = get_user_by_username(username)
    if user:
        import bcrypt
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            return user
    return None


# Product functions
def get_all_categories() -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories WHERE is_active = 1 ORDER BY name")
    categories = cur.fetchall()
    conn.close()
    return categories


def get_products_by_category(category_id: int = None, search: str = None) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    
    query = "SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.is_active = 1"
    params = []
    
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)
    
    if search:
        query += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    query += " ORDER BY p.created_at DESC"
    
    cur.execute(query, params)
    products = cur.fetchall()
    conn.close()
    return products


def get_product_by_id(product_id: int) -> Optional[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,))
    product = cur.fetchone()
    conn.close()
    return product


def update_product_stock(product_id: int, quantity: int, decrease: bool = False) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if decrease:
            cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        else:
            cur.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (quantity, product_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


# Cart functions
def add_to_cart(user_id: int, product_id: int, quantity: int = 1) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        existing = cur.execute("SELECT * FROM cart WHERE user_id = ? AND product_id = ?", 
                             (user_id, product_id)).fetchone()
        
        if existing:
            cur.execute("UPDATE cart SET quantity = quantity + ? WHERE user_id = ? AND product_id = ?",
                       (quantity, user_id, product_id))
        else:
            cur.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
                       (user_id, product_id, quantity))
        
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def get_cart_items(user_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.*, p.name, p.price, p.image_url, p.stock 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?
        ORDER BY c.created_at DESC
    """, (user_id,))
    items = cur.fetchall()
    conn.close()
    return items


def update_cart_item(user_id: int, product_id: int, quantity: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if quantity <= 0:
            cur.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        else:
            cur.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?",
                       (quantity, user_id, product_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def clear_cart(user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


# Order functions
def create_order(user_id: int, cart_items: List, shipping_address: str, payment_method: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Calculate total
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        
        # Generate order number
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id}"
        
        # Create order
        cur.execute("""
            INSERT INTO orders (user_id, order_number, total_amount, shipping_address, payment_method)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, order_number, total, shipping_address, payment_method))
        
        order_id = cur.lastrowid
        
        # Create order items
        for item in cart_items:
            # Usar 'id' se disponível, senão usar 'product_id'
            product_id = item['id'] if 'id' in item.keys() else item['product_id']
            cur.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (order_id, product_id, item['quantity'], item['price']))
            
            # Update stock
            cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item['quantity'], product_id))
        
        # Clear cart
        cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        
        conn.commit()
        return order_id
        
    except Exception as e:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_user_orders(user_id: int) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM orders 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    """, (user_id,))
    orders = cur.fetchall()
    conn.close()
    return orders


def get_order_details(order_id: int) -> Dict:
    conn = get_conn()
    cur = conn.cursor()
    
    # Get order
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cur.fetchone()
    
    if not order:
        return None
    
    # Get order items
    cur.execute("""
        SELECT oi.*, p.name, p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    """, (order_id,))
    items = cur.fetchall()
    
    conn.close()
    return {"order": order, "items": items}


def get_all_orders() -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT o.*, u.first_name, u.last_name
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
    """)
    orders = cur.fetchall()
    conn.close()
    return orders


# Novas funções para admin - gestão de produtos
def create_product(name: str, description: str, price: float, stock: int, category_id: int, image_url: str = None, sku: str = None) -> int:
    """Criar novo produto"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO products (name, description, price, stock, category_id, image_url, sku)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, description, price, stock, category_id, image_url, sku))
        
        product_id = cur.lastrowid
        conn.commit()
        return product_id
    except Exception as e:
        print(f"Erro ao criar produto: {e}")
        return None
    finally:
        conn.close()


def update_product(product_id: int, name: str = None, description: str = None, 
                  price: float = None, stock: int = None, category_id: int = None, 
                  image_url: str = None, sku: str = None) -> bool:
    """Atualizar produto existente"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Verificar se o produto existe
        cur.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        if not cur.fetchone():
            print(f"Produto com ID {product_id} não encontrado")
            return False
        
        # Construir query dinâmica
        fields_to_update = []
        values = []
        
        if name is not None:
            fields_to_update.append('name = ?')
            values.append(name)
        if description is not None:
            fields_to_update.append('description = ?')
            values.append(description)
        if price is not None:
            fields_to_update.append('price = ?')
            values.append(price)
        if stock is not None:
            fields_to_update.append('stock = ?')
            values.append(stock)
        if category_id is not None:
            fields_to_update.append('category_id = ?')
            values.append(category_id)
        if image_url is not None:
            fields_to_update.append('image_url = ?')
            values.append(image_url)
        if sku is not None:
            fields_to_update.append('sku = ?')
            values.append(sku)
        
        if fields_to_update:
            import time
            fields_to_update.append('updated_at = ?')
            values.append(int(time.time()))
            
            query = f"UPDATE products SET {', '.join(fields_to_update)} WHERE id = ?"
            values.append(product_id)
            
            cur.execute(query, values)
            conn.commit()
            
            # Verificar se a atualização foi bem-sucedida
            rows_affected = cur.rowcount
            return rows_affected > 0
        else:
            return False
            
    except Exception as e:
        print(f"Erro ao atualizar produto: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_product(product_id: int) -> bool:
    """Desativar produto (soft delete)"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao deletar produto: {e}")
        return False
    finally:
        conn.close()


def update_order_status(order_id: int, status: str) -> bool:
    """Atualizar status do pedido"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        import time
        cur.execute("""
            UPDATE orders 
            SET status = ?, updated_at = ? 
            WHERE id = ?
        """, (status, int(time.time()), order_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar status do pedido: {e}")
        return False
    finally:
        conn.close()


def get_order_details_full(order_id: int):
    """Obter detalhes completos do pedido incluindo itens"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get order info
    cur.execute("""
        SELECT o.*, u.first_name, u.last_name, u.email
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        WHERE o.id = ?
    """, (order_id,))
    order = cur.fetchone()
    
    if not order:
        return None
    
    # Get order items 
    cur.execute("""
        SELECT oi.*, p.name as product_name, p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    """, (order_id,))
    items = cur.fetchall()
    
    conn.close()
    return {"order": order, "items": items}


# Payment functions
def create_payment_transaction(order_id: int, transaction_id: str, payment_method: str, 
                             amount: float, **kwargs) -> int:
    """Criar nova transação de pagamento"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO payment_transactions (
                order_id, transaction_id, payment_method, amount, status,
                gateway_response, pix_key, pix_qr_code, boleto_number, 
                boleto_barcode, boleto_due_date, card_last_four, 
                card_brand, installments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, transaction_id, payment_method, amount, kwargs.get('status', 'pending'),
            kwargs.get('gateway_response'), kwargs.get('pix_key'), kwargs.get('pix_qr_code'),
            kwargs.get('boleto_number'), kwargs.get('boleto_barcode'), kwargs.get('boleto_due_date'),
            kwargs.get('card_last_four'), kwargs.get('card_brand'), kwargs.get('installments', 1)
        ))
        
        payment_id = cur.lastrowid
        conn.commit()
        return payment_id
    except Exception as e:
        conn.rollback()
        return None
    finally:
        conn.close()


def update_payment_status(transaction_id: str, status: str, gateway_response: str = None) -> bool:
    """Atualizar status do pagamento"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        import time
        cur.execute("""
            UPDATE payment_transactions 
            SET status = ?, gateway_response = ?, updated_at = ?
            WHERE transaction_id = ?
        """, (status, gateway_response, int(time.time()), transaction_id))
        
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()


def get_payment_transaction(transaction_id: str):
    """Obter transação de pagamento por ID"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM payment_transactions WHERE transaction_id = ?", (transaction_id,))
    transaction = cur.fetchone()
    conn.close()
    return transaction


def get_order_payments(order_id: int):
    """Obter pagamentos de um pedido"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM payment_transactions 
        WHERE order_id = ? 
        ORDER BY created_at DESC
    """, (order_id,))
    payments = cur.fetchall()
    conn.close()
    return payments


def create_payment_notification(transaction_id: str, notification_type: str, 
                               status: str, message: str = None) -> int:
    """Criar notificação de pagamento"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        import time
        cur.execute("""
            INSERT INTO payment_notifications (
                transaction_id, notification_type, status, message, processed_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (transaction_id, notification_type, status, message, int(time.time())))
        
        notification_id = cur.lastrowid
        conn.commit()
        return notification_id
    except Exception as e:
        return None
    finally:
        conn.close()


def get_payment_notifications(transaction_id: str = None):
    """Obter notificações de pagamento"""
    conn = get_conn()
    cur = conn.cursor()
    
    if transaction_id:
        cur.execute("""
            SELECT * FROM payment_notifications 
            WHERE transaction_id = ? 
            ORDER BY created_at DESC
        """, (transaction_id,))
    else:
        cur.execute("""
            SELECT * FROM payment_notifications 
            ORDER BY created_at DESC
        """)
    
    notifications = cur.fetchall()
    conn.close()
    return notifications


def get_payment_methods_config():
    """Obter configuração dos métodos de pagamento"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM payment_methods_config 
        WHERE is_active = 1 
        ORDER BY method_name
    """)
    methods = cur.fetchall()
    conn.close()
    return methods


def update_payment_method_config(method_name: str, is_active: bool = None, 
                                processing_fee: float = None, min_amount: float = None,
                                max_amount: float = None, config_data: str = None) -> bool:
    """Atualizar configuração de método de pagamento"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Construir query dinâmica
        fields_to_update = []
        values = []
        
        if is_active is not None:
            fields_to_update.append('is_active = ?')
            values.append(is_active)
        if processing_fee is not None:
            fields_to_update.append('processing_fee = ?')
            values.append(processing_fee)
        if min_amount is not None:
            fields_to_update.append('min_amount = ?')
            values.append(min_amount)
        if max_amount is not None:
            fields_to_update.append('max_amount = ?')
            values.append(max_amount)
        if config_data is not None:
            fields_to_update.append('config_data = ?')
            values.append(config_data)
        
        if fields_to_update:
            query = f"UPDATE payment_methods_config SET {', '.join(fields_to_update)} WHERE method_name = ?"
            values.append(method_name)
            
            cur.execute(query, values)
            conn.commit()
            return True
        return False
    except Exception as e:
        return False
    finally:
        conn.close()


def seed_payment_methods():
    """Inserir métodos de pagamento padrão"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Verificar se já existem métodos
        cur.execute("SELECT COUNT(*) FROM payment_methods_config")
        count = cur.fetchone()[0]
        
        if count == 0:
            payment_methods = [
                ("PIX", 1, 0.00, 0.01, 999999.99, '{"instant": true, "qr_code": true}'),
                ("Cartão de Crédito", 1, 2.99, 1.00, 999999.99, '{"installments": true, "brands": ["visa", "mastercard", "elo"]}'),
                ("Cartão de Débito", 1, 1.50, 1.00, 999999.99, '{"installments": false, "brands": ["visa", "mastercard", "elo"], "instant": true}'),
                ("Boleto Bancário", 1, 0.00, 1.00, 999999.99, '{"due_days": 3, "bank_slip": true}')
            ]
            
            for method_name, is_active, processing_fee, min_amount, max_amount, config_data in payment_methods:
                cur.execute("""
                    INSERT INTO payment_methods_config (
                        method_name, is_active, processing_fee, min_amount, max_amount, config_data
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (method_name, is_active, processing_fee, min_amount, max_amount, config_data))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        conn.close()
