from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user, token_service
from app.db.db_connection import get_db
from app.models.models import Usuario
from app.schemas.schemas import AuthResponse, UsuarioCambioPassword, UsuarioCreate, UsuarioLogin
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario_in: UsuarioCreate, db: Session = Depends(get_db)):
    usuario = auth_service.registrar_usuario(db=db, obj_in=usuario_in)
    access_token = token_service.create_access_token(usuario)
    return AuthResponse(
        autenticado=True,
        mensaje="Usuario registrado correctamente.",
        usuario=usuario,
        access_token=access_token,
    )


@router.post("/login", response_model=AuthResponse)
def login_usuario(login_in: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = auth_service.login_usuario(db=db, obj_in=login_in)
    access_token = token_service.create_access_token(usuario)
    return AuthResponse(
        autenticado=True,
        mensaje="Inicio de sesion correcto.",
        usuario=usuario,
        access_token=access_token,
    )


@router.post("/change-password", response_model=AuthResponse)
def cambiar_password(
    cambio_in: UsuarioCambioPassword,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_active_user),
):
    usuario = auth_service.cambiar_password_usuario(
        db=db,
        usuario=usuario_actual,
        password_nueva=cambio_in.password_nueva,
    )
    access_token = token_service.create_access_token(usuario)
    return AuthResponse(
        autenticado=True,
        mensaje="Contrasena actualizada correctamente.",
        usuario=usuario,
        access_token=access_token,
    )
