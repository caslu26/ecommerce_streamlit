# Guia Prático de Implementação - Melhorias Críticas

## 🚀 Implementação Passo a Passo

Este guia fornece instruções práticas e detalhadas para implementar as melhorias críticas do sistema e-commerce.

---

## 📋 Checklist de Preparação

### ✅ Pré-requisitos

- [ ] Python 3.11+ instalado
- [ ] Docker e Docker Compose instalados
- [ ] Git configurado
- [ ] Editor de código (VS Code recomendado)
- [ ] Acesso a servidor de produção

### ✅ Ferramentas Necessárias

- [ ] PostgreSQL 15+
- [ ] Redis 7+
- [ ] Nginx (para produção)
- [ ] Certificado SSL
- [ ] Domínio configurado

---

## 🏗️ Fase 1: Setup Inicial (Dia 1-2)

### Passo 1: Criar Estrutura do Projeto

```bash
# Criar diretório do projeto
mkdir ecommerce_v2
cd ecommerce_v2

# Criar estrutura de pastas
mkdir -p app/{models,schemas,services,repositories,api,middleware,utils}
mkdir -p tests
mkdir -p migrations
mkdir -p scripts

# Criar arquivos __init__.py
touch app/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
touch app/repositories/__init__.py
touch app/api/__init__.py
touch app/middleware/__init__.py
touch app/utils/__init__.py
touch tests/__init__.py
```

### Passo 2: Configurar Ambiente Virtual

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install fastapi uvicorn sqlalchemy psycopg2-binary
pip install pytest pytest-asyncio pytest-cov
pip install python-jose[cryptography] passlib[bcrypt]
pip install structlog python-multipart
pip install alembic redis
```

### Passo 3: Criar requirements.txt

```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
structlog==23.2.0
python-multipart==0.0.6
redis==5.0.1
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
```

---

## 🗄️ Fase 2: Configuração do Banco (Dia 3-4)

### Passo 1: Setup PostgreSQL com Docker

```yaml
# docker-compose.yml
version: "3.8"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ecommerce
      POSTGRES_USER: ecommerce_user
      POSTGRES_PASSWORD: ecommerce_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Passo 2: Configurar Conexão com Banco

```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Passo 3: Configurar Alembic

```bash
# Inicializar Alembic
alembic init migrations

# Configurar alembic.ini
# Editar migrations/env.py
```

```python
# migrations/env.py (configuração)
from app.database import Base
from app.models import *  # Importar todos os modelos

target_metadata = Base.metadata
```

### Passo 4: Criar Primeira Migration

```bash
# Criar migration inicial
alembic revision --autogenerate -m "Initial migration"

# Aplicar migration
alembic upgrade head
```

---

## 🔧 Fase 3: Modelos e Schemas (Dia 5-6)

### Passo 1: Criar Modelos SQLAlchemy

```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20))
    role = Column(String(20), default="customer")
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Passo 2: Criar Schemas Pydantic

```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str

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
```

### Passo 3: Criar Repository Pattern

```python
# app/repositories/user_repository.py
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from typing import Optional

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def create(self, user_data: UserCreate, password_hash: str) -> User:
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
```

---

## 🚀 Fase 4: FastAPI Core (Dia 7-10)

### Passo 1: Criar Aplicação Principal

```python
# app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, products, orders, payments
from app.middleware.logging import setup_logging
from app.middleware.security import add_security_headers

app = FastAPI(
    title="E-commerce API",
    description="API completa para sistema e-commerce",
    version="2.0.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar adequadamente para produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(add_security_headers)
setup_logging()

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])

@app.get("/")
async def root():
    return {"message": "E-commerce API v2.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Passo 2: Sistema de Autenticação

```python
# app/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.config import settings
from app.repositories.user_repository import UserRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt

    def authenticate_user(self, username: str, password: str):
        user = self.user_repo.get_by_username(username)
        if not user:
            return False
        if not self.verify_password(password, user.password_hash):
            return False
        return user
```

### Passo 3: Endpoints de Autenticação

```python
# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from datetime import timedelta

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)

    # Verificar se usuário já existe
    if user_repo.get_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already registered")

    if user_repo.get_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Criar usuário
    password_hash = auth_service.get_password_hash(user_data.password)
    user = user_repo.create(user_data, password_hash)

    return user

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)

    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}
```

---

## 🧪 Fase 5: Testes (Dia 11-14)

### Passo 1: Configurar Ambiente de Testes

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(session):
    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)

@pytest.fixture
def test_user(session):
    from app.models.user import User
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="$2b$12$hash",  # Hash de "password"
        first_name="Test",
        last_name="User"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
```

### Passo 2: Testes Unitários

```python
# tests/test_auth.py
import pytest
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository

def test_verify_password():
    auth_service = AuthService(None)
    password = "testpassword"
    hashed = auth_service.get_password_hash(password)

    assert auth_service.verify_password(password, hashed)
    assert not auth_service.verify_password("wrongpassword", hashed)

def test_create_access_token():
    auth_service = AuthService(None)
    data = {"sub": "testuser"}
    token = auth_service.create_access_token(data)

    assert token is not None
    assert isinstance(token, str)
```

### Passo 3: Testes de Integração

```python
# tests/test_api.py
def test_register_user(client):
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
        "first_name": "New",
        "last_name": "User"
    }

    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    assert response.json()["username"] == "newuser"

def test_login(client, test_user):
    login_data = {
        "username": "testuser",
        "password": "password"
    }

    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Passo 4: Executar Testes

```bash
# Executar todos os testes
pytest

# Executar com cobertura
pytest --cov=app --cov-report=html

# Executar testes específicos
pytest tests/test_auth.py -v
```

---

## 🛡️ Fase 6: Segurança (Dia 15-18)

### Passo 1: Validação de Dados

```python
# app/schemas/product.py
from pydantic import BaseModel, validator, Field
from typing import Optional
from decimal import Decimal

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

    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        return v
```

### Passo 2: Rate Limiting

```python
# app/middleware/rate_limiting.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

def setup_rate_limiting(app):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Uso nos endpoints
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, user_data: UserLogin):
    # Implementação do login
    pass
```

### Passo 3: Headers de Segurança

```python
# app/middleware/security.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response
```

---

## 📊 Fase 7: Logs e Monitoramento (Dia 19-21)

### Passo 1: Configurar Logging Estruturado

```python
# app/middleware/logging.py
import structlog
import logging
import sys
from app.config import settings

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
```

### Passo 2: Middleware de Logging

```python
# app/middleware/logging.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import structlog

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log da requisição
        logger.info(
            "API Request",
            method=request.method,
            path=request.url.path,
            event_type="api_request"
        )

        # Processar requisição
        response = await call_next(request)

        # Log da resposta
        process_time = time.time() - start_time
        logger.info(
            "API Response",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=process_time,
            event_type="api_response"
        )

        return response
```

---

## 🚀 Fase 8: Deploy (Dia 22-28)

### Passo 1: Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Expor porta
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Passo 2: Docker Compose para Produção

```yaml
# docker-compose.prod.yml
version: "3.8"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/ecommerce
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ecommerce
      POSTGRES_USER: ecommerce_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

### Passo 3: Deploy

```bash
# Build e deploy
docker-compose -f docker-compose.prod.yml up -d

# Verificar logs
docker-compose -f docker-compose.prod.yml logs -f

# Verificar status
docker-compose -f docker-compose.prod.yml ps
```

---

## ✅ Checklist de Validação

### Funcionalidades

- [ ] Autenticação JWT funcionando
- [ ] CRUD de produtos implementado
- [ ] Sistema de pedidos funcionando
- [ ] Pagamentos integrados
- [ ] Dashboard administrativo

### Segurança

- [ ] Validação de dados implementada
- [ ] Rate limiting configurado
- [ ] Headers de segurança
- [ ] Sanitização de inputs
- [ ] Logs de auditoria

### Performance

- [ ] Tempo de resposta < 200ms
- [ ] Queries otimizadas
- [ ] Cache implementado
- [ ] Índices de banco criados

### Testes

- [ ] 80%+ cobertura de testes
- [ ] Testes unitários passando
- [ ] Testes de integração passando
- [ ] CI/CD funcionando

### Deploy

- [ ] Docker funcionando
- [ ] SSL configurado
- [ ] Monitoramento ativo
- [ ] Backup configurado

---

## 🆘 Troubleshooting

### Problemas Comuns

#### 1. Erro de Conexão com Banco

```bash
# Verificar se PostgreSQL está rodando
docker-compose ps

# Verificar logs
docker-compose logs postgres

# Recriar container
docker-compose down
docker-compose up -d postgres
```

#### 2. Erro de Migração

```bash
# Verificar status das migrations
alembic current

# Aplicar migrations pendentes
alembic upgrade head

# Reverter migration
alembic downgrade -1
```

#### 3. Erro de Testes

```bash
# Limpar cache de testes
pytest --cache-clear

# Executar com verbose
pytest -v

# Executar teste específico
pytest tests/test_auth.py::test_login -v
```

#### 4. Erro de Deploy

```bash
# Verificar logs da aplicação
docker-compose logs app

# Verificar se containers estão rodando
docker-compose ps

# Recriar containers
docker-compose down
docker-compose up -d --build
```

---

## 📞 Suporte

### Recursos Úteis

- [Documentação FastAPI](https://fastapi.tiangolo.com/)
- [Documentação SQLAlchemy](https://docs.sqlalchemy.org/)
- [Documentação Pytest](https://docs.pytest.org/)
- [Documentação Docker](https://docs.docker.com/)

### Contatos

- **Desenvolvedor**: [seu-email@exemplo.com]
- **DevOps**: [devops@exemplo.com]
- **Suporte**: [suporte@exemplo.com]

---

**Guia criado em**: $(date)
**Versão**: 1.0
**Próxima atualização**: Conforme necessário
