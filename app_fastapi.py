"""
Sistema E-commerce FastAPI - Versão 2.0
Implementação das melhorias críticas identificadas
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List
import json
import logging
import structlog

# Configurar logging estruturado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Importar módulos existentes
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_db_connection, init_database
from payment_system import PaymentProcessor, PaymentUI

# Configurações
class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    DATABASE_URL = "sqlite:///./ecommerce.db"

settings = Settings()

# Criar aplicação FastAPI
app = FastAPI(
    title="E-commerce API v2.0",
    description="Sistema e-commerce com melhorias críticas implementadas",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de Logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    
    # Log da requisição
    logger.info(
        "API Request",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host,
        event_type="api_request"
    )
    
    # Processar requisição
    response = await call_next(request)
    
    # Log da resposta
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(
        "API Response",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time=process_time,
        event_type="api_response"
    )
    
    return response

# Middleware de Segurança
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Headers de segurança
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Schemas Pydantic
from pydantic import BaseModel, EmailStr, validator, Field
from decimal import Decimal

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserResponse(UserBase):
    id: int
    role: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    stock: int = Field(..., ge=0)
    category_id: int = Field(..., gt=0)
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    sku: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    user_id: int
    total: Decimal = Field(..., gt=0, decimal_places=2)
    status: str = "pending"

class OrderCreate(OrderBase):
    items: List[dict]  # Lista de produtos com quantidade

class OrderResponse(OrderBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class PaymentBase(BaseModel):
    order_id: int
    payment_method: str
    amount: Decimal = Field(..., gt=0, decimal_places=2)

class PaymentCreate(PaymentBase):
    pass

class PaymentResponse(PaymentBase):
    id: int
    transaction_id: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Sistema de Autenticação JWT
import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.PyJWTError:
        return None

# Dependências
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Buscar usuário no banco
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "id": user[0],
        "username": user[1],
        "email": user[2],
        "first_name": user[4],
        "last_name": user[5],
        "role": user[7],
        "status": user[8]
    }

# Endpoints

@app.get("/")
async def root():
    return {
        "message": "E-commerce API v2.0",
        "version": "2.0.0",
        "status": "active",
        "features": [
            "JWT Authentication",
            "Structured Logging",
            "Security Headers",
            "Input Validation",
            "RESTful API"
        ]
    }

@app.get("/health")
async def health_check():
    try:
        # Verificar conexão com banco
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# Autenticação
@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Registrar novo usuário"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se usuário já existe
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                      (user_data.username, user_data.email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Username or email already registered"
            )
        
        # Criar usuário
        password_hash = get_password_hash(user_data.password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, first_name, last_name, phone, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'customer', 'active', ?)
        """, (
            user_data.username,
            user_data.email,
            password_hash,
            user_data.first_name,
            user_data.last_name,
            user_data.phone,
            int(datetime.now().timestamp())
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info("User registered", user_id=user_id, username=user_data.username)
        
        return {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "phone": user_data.phone,
            "role": "customer",
            "status": "active",
            "created_at": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Registration failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/auth/login")
async def login(username: str, password: str):
    """Login do usuário"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not verify_password(password, user[3]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user[1]}, expires_delta=access_token_expires
        )
        
        logger.info("User logged in", user_id=user[0], username=username)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "first_name": user[4],
                "last_name": user[5],
                "role": user[7]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Produtos
@app.get("/api/v1/products", response_model=List[ProductResponse])
async def get_products(
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """Listar produtos com filtros"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM products WHERE is_active = 1"
        params = []
        
        if category_id:
            query += " AND category_id = ?"
            params.append(category_id)
        
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        
        cursor.execute(query, params)
        products = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": p[0],
                "name": p[1],
                "description": p[2],
                "price": Decimal(str(p[3])),
                "stock": p[4],
                "category_id": p[5],
                "sku": p[7],
                "is_active": bool(p[8]),
                "created_at": datetime.fromtimestamp(p[9]),
                "updated_at": datetime.fromtimestamp(p[10]) if p[10] else None
            }
            for p in products
        ]
        
    except Exception as e:
        logger.error("Failed to get products", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    """Obter produto por ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,))
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {
            "id": product[0],
            "name": product[1],
            "description": product[2],
            "price": Decimal(str(product[3])),
            "stock": product[4],
            "category_id": product[5],
            "sku": product[7],
            "is_active": bool(product[8]),
            "created_at": datetime.fromtimestamp(product[9]),
            "updated_at": datetime.fromtimestamp(product[10]) if product[10] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get product", product_id=product_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/products", response_model=ProductResponse)
async def create_product(product_data: ProductCreate, current_user: dict = Depends(get_current_user)):
    """Criar novo produto (apenas admin)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Gerar SKU único
        sku = f"PROD-{int(datetime.now().timestamp())}"
        
        cursor.execute("""
            INSERT INTO products (name, description, price, stock, category_id, sku, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            product_data.name,
            product_data.description,
            float(product_data.price),
            product_data.stock,
            product_data.category_id,
            sku,
            int(datetime.now().timestamp()),
            int(datetime.now().timestamp())
        ))
        
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info("Product created", product_id=product_id, name=product_data.name)
        
        return {
            "id": product_id,
            "name": product_data.name,
            "description": product_data.description,
            "price": product_data.price,
            "stock": product_data.stock,
            "category_id": product_data.category_id,
            "sku": sku,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error("Failed to create product", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Pedidos
@app.get("/api/v1/orders", response_model=List[OrderResponse])
async def get_orders(current_user: dict = Depends(get_current_user)):
    """Listar pedidos do usuário"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if current_user["role"] == "admin":
            cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", 
                          (current_user["id"],))
        
        orders = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": o[0],
                "user_id": o[1],
                "total": Decimal(str(o[2])),
                "status": o[3],
                "created_at": datetime.fromtimestamp(o[4]),
                "updated_at": datetime.fromtimestamp(o[5]) if o[5] else None
            }
            for o in orders
        ]
        
    except Exception as e:
        logger.error("Failed to get orders", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/orders", response_model=OrderResponse)
async def create_order(order_data: OrderCreate, current_user: dict = Depends(get_current_user)):
    """Criar novo pedido"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se produtos existem e têm estoque
        for item in order_data.items:
            cursor.execute("SELECT stock FROM products WHERE id = ? AND is_active = 1", (item["product_id"],))
            product = cursor.fetchone()
            
            if not product:
                conn.close()
                raise HTTPException(status_code=400, detail=f"Product {item['product_id']} not found")
            
            if product[0] < item["quantity"]:
                conn.close()
                raise HTTPException(status_code=400, detail=f"Insufficient stock for product {item['product_id']}")
        
        # Criar pedido
        cursor.execute("""
            INSERT INTO orders (user_id, total, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            current_user["id"],
            float(order_data.total),
            order_data.status,
            int(datetime.now().timestamp()),
            int(datetime.now().timestamp())
        ))
        
        order_id = cursor.lastrowid
        
        # Adicionar itens do pedido
        for item in order_data.items:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, (SELECT price FROM products WHERE id = ?))
            """, (order_id, item["product_id"], item["quantity"], item["product_id"]))
            
            # Atualizar estoque
            cursor.execute("""
                UPDATE products SET stock = stock - ?, updated_at = ?
                WHERE id = ?
            """, (item["quantity"], int(datetime.now().timestamp()), item["product_id"]))
        
        conn.commit()
        conn.close()
        
        logger.info("Order created", order_id=order_id, user_id=current_user["id"])
        
        return {
            "id": order_id,
            "user_id": current_user["id"],
            "total": order_data.total,
            "status": order_data.status,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create order", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Pagamentos
@app.get("/api/v1/payments", response_model=List[PaymentResponse])
async def get_payments(current_user: dict = Depends(get_current_user)):
    """Listar pagamentos do usuário"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if current_user["role"] == "admin":
            cursor.execute("SELECT * FROM payment_transactions ORDER BY created_at DESC")
        else:
            cursor.execute("""
                SELECT pt.* FROM payment_transactions pt
                JOIN orders o ON pt.order_id = o.id
                WHERE o.user_id = ?
                ORDER BY pt.created_at DESC
            """, (current_user["id"],))
        
        payments = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": p[0],
                "order_id": p[1],
                "payment_method": p[3],
                "amount": Decimal(str(p[4])),
                "transaction_id": p[2],
                "status": p[5],
                "created_at": datetime.fromtimestamp(p[16])
            }
            for p in payments
        ]
        
    except Exception as e:
        logger.error("Failed to get payments", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/payments", response_model=PaymentResponse)
async def create_payment(payment_data: PaymentCreate, current_user: dict = Depends(get_current_user)):
    """Processar pagamento"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se pedido existe e pertence ao usuário
        cursor.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?", 
                      (payment_data.order_id, current_user["id"]))
        order = cursor.fetchone()
        
        if not order:
            conn.close()
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Processar pagamento usando o sistema existente
        payment_processor = PaymentProcessor()
        
        # Simular dados de pagamento baseado no método
        if payment_data.payment_method == "PIX":
            result = payment_processor.process_pix({
                "amount": float(payment_data.amount)
            })
        elif payment_data.payment_method == "Cartão de Crédito":
            result = payment_processor.process_credit_card({
                "number": "4111111111111111",  # Cartão de teste
                "expiry": "12/25",
                "cvv": "123",
                "name": "TEST USER",
                "amount": float(payment_data.amount)
            })
        elif payment_data.payment_method == "Cartão de Débito":
            result = payment_processor.process_debit_card({
                "number": "4111111111111111",  # Cartão de teste
                "expiry": "12/25",
                "cvv": "123",
                "name": "TEST USER",
                "amount": float(payment_data.amount)
            })
        else:
            conn.close()
            raise HTTPException(status_code=400, detail="Invalid payment method")
        
        if not result.get("success"):
            conn.close()
            raise HTTPException(status_code=400, detail=result.get("error", "Payment failed"))
        
        # Salvar transação no banco
        cursor.execute("""
            INSERT INTO payment_transactions 
            (order_id, transaction_id, payment_method, amount, status, gateway_response, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payment_data.order_id,
            result["transaction_id"],
            payment_data.payment_method,
            float(payment_data.amount),
            result["status"],
            json.dumps(result.get("gateway_response", {})),
            int(datetime.now().timestamp()),
            int(datetime.now().timestamp())
        ))
        
        payment_id = cursor.lastrowid
        
        # Atualizar status do pedido
        cursor.execute("""
            UPDATE orders SET status = 'paid', updated_at = ?
            WHERE id = ?
        """, (int(datetime.now().timestamp()), payment_data.order_id))
        
        conn.commit()
        conn.close()
        
        logger.info("Payment processed", payment_id=payment_id, transaction_id=result["transaction_id"])
        
        return {
            "id": payment_id,
            "order_id": payment_data.order_id,
            "payment_method": payment_data.payment_method,
            "amount": payment_data.amount,
            "transaction_id": result["transaction_id"],
            "status": result["status"],
            "created_at": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process payment", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Dashboard Admin
@app.get("/api/v1/admin/dashboard")
async def admin_dashboard(current_user: dict = Depends(get_current_user)):
    """Dashboard administrativo"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Estatísticas gerais
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        total_products = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total) FROM orders WHERE status = 'paid'")
        total_revenue = cursor.fetchone()[0] or 0
        
        # Vendas por mês (últimos 6 meses)
        cursor.execute("""
            SELECT strftime('%Y-%m', datetime(created_at, 'unixepoch')) as month,
                   COUNT(*) as orders,
                   SUM(total) as revenue
            FROM orders 
            WHERE status = 'paid' 
            AND created_at >= ?
            GROUP BY month
            ORDER BY month DESC
        """, (int((datetime.now() - timedelta(days=180)).timestamp()),))
        
        monthly_sales = [
            {
                "month": row[0],
                "orders": row[1],
                "revenue": float(row[2]) if row[2] else 0
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "total_users": total_users,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "monthly_sales": monthly_sales,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get admin dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Inicializar banco de dados
@app.on_event("startup")
async def startup_event():
    """Inicializar banco de dados na startup"""
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))

if __name__ == "__main__":
    # Instalar dependências necessárias
    import subprocess
    import sys
    
    try:
        import structlog
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "structlog"])
        import structlog
    
    try:
        import jwt
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyJWT"])
        import jwt
    
    try:
        from passlib.context import CryptContext
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "passlib[bcrypt]"])
        from passlib.context import CryptContext
    
    try:
        from pydantic import BaseModel, EmailStr, validator, Field
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pydantic[email]"])
        from pydantic import BaseModel, EmailStr, validator, Field
    
    # Executar servidor
    uvicorn.run(
        "app_fastapi:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
