"""
CondoOS - Sistema de Gerenciamento de Ordens de Serviço para Condomínios
Backend FastAPI
"""

from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum
import os
import json
import uuid
import shutil
from pathlib import Path

# Configuração do app
app = FastAPI(
    title="CondoOS API",
    description="API para gerenciamento de ordens de serviço de condomínios",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Montar arquivos estáticos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ==================== ENUMS ====================

class UserRole(str, Enum):
    MORADOR = "morador"
    SINDICO = "sindico"
    FUNCIONARIO = "funcionario"
    ADMIN = "admin"

class OrderStatus(str, Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"

class Priority(str, Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"

class Category(str, Enum):
    ELETRICA = "eletrica"
    HIDRAULICA = "hidraulica"
    LIMPEZA = "limpeza"
    SEGURANCA = "seguranca"
    ESTRUTURAL = "estrutural"
    JARDINAGEM = "jardinagem"
    OUTROS = "outros"

# ==================== MODELOS ====================

class User(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    apartment: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime
    password: str  # Em produção, usar hash

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: UserRole
    apartment: Optional[str] = None
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    apartment: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime

class Order(BaseModel):
    id: str
    title: str
    description: str
    category: Category
    priority: Priority
    status: OrderStatus
    requester_id: str
    requester_name: str
    apartment: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_name: Optional[str] = None
    photos: List[str] = []
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

class OrderCreate(BaseModel):
    title: str
    description: str
    category: Category
    priority: Priority
    apartment: Optional[str] = None
    estimated_completion: Optional[datetime] = None

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    assigned_to: Optional[str] = None
    priority: Optional[Priority] = None
    description: Optional[str] = None

class Comment(BaseModel):
    id: str
    order_id: str
    user_id: str
    user_name: str
    user_role: UserRole
    content: str
    created_at: datetime
    is_internal: bool = False

class CommentCreate(BaseModel):
    content: str
    is_internal: bool = False

class Notification(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    order_id: Optional[str] = None
    read: bool = False
    created_at: datetime

class Stats(BaseModel):
    total_orders: int
    pending_orders: int
    in_progress_orders: int
    completed_orders: int
    cancelled_orders: int
    avg_resolution_time_hours: float
    orders_by_category: dict
    orders_by_priority: dict

# ==================== BANCO DE DADOS SIMULADO ====================

class Database:
    def __init__(self):
        self.users: List[User] = []
        self.orders: List[Order] = []
        self.comments: List[Comment] = []
        self.notifications: List[Notification] = []
        self._load_data()
        self._seed_data()
    
    def _load_data(self):
        try:
            if (DATA_DIR / "users.json").exists():
                with open(DATA_DIR / "users.json", "r") as f:
                    data = json.load(f)
                    self.users = [User(**u) for u in data]
            if (DATA_DIR / "orders.json").exists():
                with open(DATA_DIR / "orders.json", "r") as f:
                    data = json.load(f)
                    self.orders = [Order(**o) for o in data]
            if (DATA_DIR / "comments.json").exists():
                with open(DATA_DIR / "comments.json", "r") as f:
                    data = json.load(f)
                    self.comments = [Comment(**c) for c in data]
            if (DATA_DIR / "notifications.json").exists():
                with open(DATA_DIR / "notifications.json", "r") as f:
                    data = json.load(f)
                    self.notifications = [Notification(**n) for n in data]
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
    
    def _save_data(self):
        try:
            with open(DATA_DIR / "users.json", "w") as f:
                json.dump([u.model_dump() for u in self.users], f, default=str, indent=2)
            with open(DATA_DIR / "orders.json", "w") as f:
                json.dump([o.model_dump() for o in self.orders], f, default=str, indent=2)
            with open(DATA_DIR / "comments.json", "w") as f:
                json.dump([c.model_dump() for c in self.comments], f, default=str, indent=2)
            with open(DATA_DIR / "notifications.json", "w") as f:
                json.dump([n.model_dump() for n in self.notifications], f, default=str, indent=2)
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")
    
    def _seed_data(self):
        """Cria dados iniciais se não existirem"""
        if not self.users:
            # Usuários de teste
            self.users = [
                User(
                    id="1",
                    name="Administrador",
                    email="admin@condo.com",
                    role=UserRole.ADMIN,
                    created_at=datetime.now(),
                    password="admin123"
                ),
                User(
                    id="2",
                    name="Síndico João",
                    email="sindico@condo.com",
                    role=UserRole.SINDICO,
                    phone="(11) 99999-1111",
                    created_at=datetime.now(),
                    password="sindico123"
                ),
                User(
                    id="3",
                    name="Maria Moradora",
                    email="morador@condo.com",
                    role=UserRole.MORADOR,
                    apartment="101A",
                    phone="(11) 99999-2222",
                    created_at=datetime.now(),
                    password="morador123"
                ),
                User(
                    id="4",
                    name="Pedro Funcionário",
                    email="funcionario@condo.com",
                    role=UserRole.FUNCIONARIO,
                    phone="(11) 99999-3333",
                    created_at=datetime.now(),
                    password="func123"
                ),
            ]
            self._save_data()

db = Database()

# ==================== AUTENTICAÇÃO ====================

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Valida token e retorna usuário atual"""
    token = credentials.credentials
    # Em produção, validar JWT corretamente
    try:
        user_id = token.replace("token_", "")
        user = next((u for u in db.users if u.id == user_id), None)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")

def require_role(roles: List[UserRole]):
    """Decorator para requerer papéis específicos"""
    def role_checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Acesso negado")
        return user
    return role_checker

# ==================== ENDPOINTS DE AUTENTICAÇÃO ====================

@app.post("/api/auth/login", response_model=dict)
async def login(credentials: UserLogin):
    """Login de usuário"""
    user = next((u for u in db.users if u.email == credentials.email), None)
    if not user or user.password != credentials.password:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    # Em produção, gerar JWT real
    token = f"token_{user.id}"
    
    return {
        "token": token,
        "user": UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            apartment=user.apartment,
            phone=user.phone,
            created_at=user.created_at
        )
    }

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Retorna dados do usuário logado"""
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        apartment=user.apartment,
        phone=user.phone,
        created_at=user.created_at
    )

# ==================== ENDPOINTS DE USUÁRIOS ====================

@app.get("/api/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[UserRole] = None,
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.SINDICO]))
):
    """Lista usuários (apenas admin e síndico)"""
    users = db.users
    if role:
        users = [u for u in users if u.role == role]
    return [
        UserResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role,
            apartment=u.apartment,
            phone=u.phone,
            created_at=u.created_at
        ) for u in users
    ]

@app.post("/api/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SINDICO]))
):
    """Cria novo usuário"""
    if any(u.email == user_data.email for u in db.users):
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    new_user = User(
        id=str(len(db.users) + 1),
        name=user_data.name,
        email=user_data.email,
        role=user_data.role,
        apartment=user_data.apartment,
        phone=user_data.phone,
        created_at=datetime.now(),
        password=user_data.password
    )
    db.users.append(new_user)
    db._save_data()
    
    return UserResponse(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        role=new_user.role,
        apartment=new_user.apartment,
        phone=new_user.phone,
        created_at=new_user.created_at
    )

# ==================== ENDPOINTS DE ORDENS ====================

@app.get("/api/orders", response_model=List[Order])
async def list_orders(
    status: Optional[OrderStatus] = None,
    category: Optional[Category] = None,
    priority: Optional[Priority] = None,
    search: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Lista ordens de serviço com filtros"""
    orders = db.orders
    
    # Moradores só veem suas próprias ordens
    if user.role == UserRole.MORADOR:
        orders = [o for o in orders if o.requester_id == user.id]
    
    if status:
        orders = [o for o in orders if o.status == status]
    if category:
        orders = [o for o in orders if o.category == category]
    if priority:
        orders = [o for o in orders if o.priority == priority]
    if search:
        search_lower = search.lower()
        orders = [o for o in orders if search_lower in o.title.lower() or search_lower in o.description.lower()]
    
    return sorted(orders, key=lambda x: x.created_at, reverse=True)

@app.get("/api/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, user: User = Depends(get_current_user)):
    """Retorna detalhes de uma ordem"""
    order = next((o for o in db.orders if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Ordem não encontrada")
    
    # Moradores só podem ver suas próprias ordens
    if user.role == UserRole.MORADOR and order.requester_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    return order

@app.post("/api/orders", response_model=Order)
async def create_order(
    order_data: OrderCreate,
    user: User = Depends(get_current_user)
):
    """Cria nova ordem de serviço"""
    new_order = Order(
        id=str(uuid.uuid4()),
        title=order_data.title,
        description=order_data.description,
        category=order_data.category,
        priority=order_data.priority,
        status=OrderStatus.PENDENTE,
        requester_id=user.id,
        requester_name=user.name,
        apartment=order_data.apartment or user.apartment,
        photos=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        estimated_completion=order_data.estimated_completion
    )
    db.orders.append(new_order)
    db._save_data()
    
    # Criar notificação para síndicos e admins
    for u in db.users:
        if u.role in [UserRole.SINDICO, UserRole.ADMIN]:
            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=u.id,
                title="Nova Ordem de Serviço",
                message=f"{user.name} criou uma nova OS: {order_data.title}",
                order_id=new_order.id,
                read=False,
                created_at=datetime.now()
            )
            db.notifications.append(notification)
    db._save_data()
    
    return new_order

@app.post("/api/orders/{order_id}/photos")
async def upload_photo(
    order_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """Upload de foto para uma ordem"""
    order = next((o for o in db.orders if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Ordem não encontrada")
    
    # Apenas o solicitante ou admin/síndico pode adicionar fotos
    if user.role == UserRole.MORADOR and order.requester_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Salvar arquivo
    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = UPLOAD_DIR / file_name
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    order.photos.append(f"/uploads/{file_name}")
    order.updated_at = datetime.now()
    db._save_data()
    
    return {"photo_url": f"/uploads/{file_name}"}

@app.put("/api/orders/{order_id}", response_model=Order)
async def update_order(
    order_id: str,
    update_data: OrderUpdate,
    user: User = Depends(get_current_user)
):
    """Atualiza uma ordem de serviço"""
    order = next((o for o in db.orders if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Ordem não encontrada")
    
    # Verificar permissões
    if user.role == UserRole.MORADOR and order.requester_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    old_status = order.status
    
    if update_data.status:
        order.status = update_data.status
        if update_data.status == OrderStatus.CONCLUIDA:
            order.completed_at = datetime.now()
    
    if update_data.assigned_to:
        if user.role not in [UserRole.ADMIN, UserRole.SINDICO]:
            raise HTTPException(status_code=403, detail="Apenas admin/síndico pode atribuir")
        order.assigned_to = update_data.assigned_to
        assigned_user = next((u for u in db.users if u.id == update_data.assigned_to), None)
        if assigned_user:
            order.assigned_name = assigned_user.name
    
    if update_data.priority:
        if user.role not in [UserRole.ADMIN, UserRole.SINDICO]:
            raise HTTPException(status_code=403, detail="Apenas admin/síndico pode alterar prioridade")
        order.priority = update_data.priority
    
    if update_data.description:
        order.description = update_data.description
    
    order.updated_at = datetime.now()
    db._save_data()
    
    # Notificar sobre mudança de status
    if old_status != order.status:
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=order.requester_id,
            title="Atualização de OS",
            message=f"Sua ordem '{order.title}' foi atualizada para: {order.status.value}",
            order_id=order.id,
            read=False,
            created_at=datetime.now()
        )
        db.notifications.append(notification)
        db._save_data()
    
    return order

# ==================== ENDPOINTS DE COMENTÁRIOS ====================

@app.get("/api/orders/{order_id}/comments", response_model=List[Comment])
async def list_comments(order_id: str, user: User = Depends(get_current_user)):
    """Lista comentários de uma ordem"""
    order = next((o for o in db.orders if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Ordem não encontrada")
    
    comments = [c for c in db.comments if c.order_id == order_id]
    
    # Moradores não veem comentários internos
    if user.role == UserRole.MORADOR:
        comments = [c for c in comments if not c.is_internal]
    
    return sorted(comments, key=lambda x: x.created_at)

@app.post("/api/orders/{order_id}/comments", response_model=Comment)
async def create_comment(
    order_id: str,
    comment_data: CommentCreate,
    user: User = Depends(get_current_user)
):
    """Adiciona comentário a uma ordem"""
    order = next((o for o in db.orders if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Ordem não encontrada")
    
    # Moradores não podem criar comentários internos
    if user.role == UserRole.MORADOR and comment_data.is_internal:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Moradores só podem comentar em suas ordens
    if user.role == UserRole.MORADOR and order.requester_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    new_comment = Comment(
        id=str(uuid.uuid4()),
        order_id=order_id,
        user_id=user.id,
        user_name=user.name,
        user_role=user.role,
        content=comment_data.content,
        created_at=datetime.now(),
        is_internal=comment_data.is_internal
    )
    db.comments.append(new_comment)
    db._save_data()
    
    # Notificar solicitante sobre novo comentário
    if order.requester_id != user.id:
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=order.requester_id,
            title="Novo Comentário",
            message=f"{user.name} comentou na ordem '{order.title}'",
            order_id=order.id,
            read=False,
            created_at=datetime.now()
        )
        db.notifications.append(notification)
        db._save_data()
    
    return new_comment

# ==================== ENDPOINTS DE NOTIFICAÇÕES ====================

@app.get("/api/notifications", response_model=List[Notification])
async def list_notifications(user: User = Depends(get_current_user)):
    """Lista notificações do usuário"""
    notifications = [n for n in db.notifications if n.user_id == user.id]
    return sorted(notifications, key=lambda x: x.created_at, reverse=True)

@app.get("/api/notifications/unread-count", response_model=dict)
async def unread_count(user: User = Depends(get_current_user)):
    """Retorna contagem de notificações não lidas"""
    count = len([n for n in db.notifications if n.user_id == user.id and not n.read])
    return {"count": count}

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: User = Depends(get_current_user)
):
    """Marca notificação como lida"""
    notification = next((n for n in db.notifications if n.id == notification_id), None)
    if not notification or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    notification.read = True
    db._save_data()
    return {"success": True}

@app.put("/api/notifications/read-all")
async def mark_all_notifications_read(user: User = Depends(get_current_user)):
    """Marca todas as notificações como lidas"""
    for n in db.notifications:
        if n.user_id == user.id:
            n.read = True
    db._save_data()
    return {"success": True}

# ==================== ENDPOINTS DE RELATÓRIOS ====================

@app.get("/api/reports/stats", response_model=Stats)
async def get_stats(user: User = Depends(require_role([UserRole.ADMIN, UserRole.SINDICO]))):
    """Retorna estatísticas do sistema"""
    orders = db.orders
    
    # Contagens por status
    pending = len([o for o in orders if o.status == OrderStatus.PENDENTE])
    in_progress = len([o for o in orders if o.status == OrderStatus.EM_ANDAMENTO])
    completed = len([o for o in orders if o.status == OrderStatus.CONCLUIDA])
    cancelled = len([o for o in orders if o.status == OrderStatus.CANCELADA])
    
    # Tempo médio de resolução
    completed_orders = [o for o in orders if o.status == OrderStatus.CONCLUIDA and o.completed_at]
    if completed_orders:
        total_hours = sum(
            (o.completed_at - o.created_at).total_seconds() / 3600 
            for o in completed_orders
        )
        avg_hours = total_hours / len(completed_orders)
    else:
        avg_hours = 0
    
    # Por categoria
    categories = {}
    for cat in Category:
        categories[cat.value] = len([o for o in orders if o.category == cat])
    
    # Por prioridade
    priorities = {}
    for pri in Priority:
        priorities[pri.value] = len([o for o in orders if o.priority == pri])
    
    return Stats(
        total_orders=len(orders),
        pending_orders=pending,
        in_progress_orders=in_progress,
        completed_orders=completed,
        cancelled_orders=cancelled,
        avg_resolution_time_hours=round(avg_hours, 2),
        orders_by_category=categories,
        orders_by_priority=priorities
    )

@app.get("/api/reports/orders-by-period")
async def orders_by_period(
    start_date: datetime,
    end_date: datetime,
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.SINDICO]))
):
    """Retorna ordens criadas em um período"""
    orders = [
        o for o in db.orders 
        if start_date <= o.created_at <= end_date
    ]
    return {"count": len(orders), "orders": orders}

# ==================== HEALTH CHECK ====================

@app.get("/api/health")
async def health_check():
    """Verifica saúde da API"""
    return {"status": "ok", "timestamp": datetime.now()}

# ==================== INICIALIZAÇÃO ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
