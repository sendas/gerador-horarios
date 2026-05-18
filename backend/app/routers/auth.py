from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.database import get_db
from app.models.user import User
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserResponse"

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "user"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

Token.model_rebuild()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username, User.is_active == True).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilizador ou palavra-passe incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/password")
def change_own_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Palavra-passe atual incorreta")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Palavra-passe alterada com sucesso"}


@router.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(User).all()


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Nome de utilizador já existe")
    if data.role not in ("admin", "user", "viewer"):
        raise HTTPException(status_code=400, detail="Role inválido (admin/user/viewer)")
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{id}", response_model=UserResponse)
def update_user(id: int, data: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{id}/reset-password")
def reset_password(id: int, data: dict, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    new_password = data.get("password")
    if not new_password:
        raise HTTPException(status_code=400, detail="Nova palavra-passe obrigatória")
    user.hashed_password = hash_password(new_password)
    db.commit()
    return {"message": "Palavra-passe redefinida"}


@router.delete("/users/{id}", status_code=204)
def delete_user(id: int, db: Session = Depends(get_db), current: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="Não podes eliminar a tua própria conta")
    db.delete(user)
    db.commit()


@router.post("/demo")
def demo_login(db: Session = Depends(get_db)):
    """Login sem password para modo demonstração."""
    from datetime import timedelta
    demo_user = db.query(User).filter(User.username == "demo").first()
    if not demo_user:
        raise HTTPException(status_code=503, detail="Modo demo não disponível")
    token = create_access_token({"sub": demo_user.username}, expires_delta=timedelta(minutes=60))
    return {"access_token": token, "token_type": "bearer", "user": UserResponse.model_validate(demo_user)}
