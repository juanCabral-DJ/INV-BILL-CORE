import hashlib
import hmac
import secrets

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.models import Usuario
from app.schemas.schemas import UsuarioCambioPassword, UsuarioCreate, UsuarioLogin


class AuthService:
    HASH_ITERATIONS = 100_000
    HASH_NAME = "sha256"
    SALT_BYTES = 16

    def registrar_usuario(self, db: Session, *, obj_in: UsuarioCreate) -> Usuario:
        correo_normalizado = obj_in.correo.strip().lower()
        username_normalizado = obj_in.username.strip().lower()
        existente = db.execute(
            select(Usuario.id).where(
                or_(Usuario.correo == correo_normalizado, func.lower(Usuario.username) == username_normalizado)
            ).limit(1)
        ).scalar_one_or_none()

        if existente:
            raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo o nombre de usuario.")

        usuario = Usuario(
            username=obj_in.username.strip(),
            correo=correo_normalizado,
            password_hash=self._hash_password(obj_in.password),
            is_active=obj_in.is_active,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    def login_usuario(self, db: Session, *, obj_in: UsuarioLogin) -> Usuario:
        identificador_normalizado = obj_in.identificador.strip().lower()
        usuarios = db.execute(
            select(Usuario).where(
                or_(
                    func.lower(Usuario.correo) == identificador_normalizado,
                    func.lower(Usuario.username) == identificador_normalizado,
                ),
                Usuario.is_active.is_(True),
            )
        ).scalars().all()

        if len(usuarios) > 1:
            raise HTTPException(
                status_code=409,
                detail="Existen usuarios duplicados para ese identificador. Debes corregir los datos antes de iniciar sesion.",
            )

        usuario = usuarios[0] if usuarios else None

        if not usuario or not self._verify_password(obj_in.password, usuario.password_hash):
            raise HTTPException(status_code=401, detail="Usuario/correo o contrasena incorrectos.")

        return usuario

    def cambiar_password(self, db: Session, *, obj_in: UsuarioCambioPassword) -> Usuario:
        if not obj_in.identificador:
            raise HTTPException(status_code=400, detail="El identificador es requerido.")

        identificador_normalizado = obj_in.identificador.strip().lower()
        usuarios = db.execute(
            select(Usuario).where(
                or_(
                    func.lower(Usuario.correo) == identificador_normalizado,
                    func.lower(Usuario.username) == identificador_normalizado,
                ),
                Usuario.is_active.is_(True),
            )
        ).scalars().all()

        if len(usuarios) > 1:
            raise HTTPException(
                status_code=409,
                detail="Existen usuarios duplicados para ese identificador. Debes corregir los datos antes de cambiar la contrasena.",
            )

        usuario = usuarios[0] if usuarios else None

        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado o inactivo.")

        if self._verify_password(obj_in.password_nueva, usuario.password_hash):
            raise HTTPException(status_code=400, detail="La nueva contrasena debe ser diferente a la actual.")

        usuario.password_hash = self._hash_password(obj_in.password_nueva)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    def cambiar_password_usuario(self, db: Session, *, usuario: Usuario, password_nueva: str) -> Usuario:
        if self._verify_password(password_nueva, usuario.password_hash):
            raise HTTPException(status_code=400, detail="La nueva contrasena debe ser diferente a la actual.")

        usuario.password_hash = self._hash_password(password_nueva)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(self.SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            self.HASH_NAME,
            password.encode("utf-8"),
            salt,
            self.HASH_ITERATIONS,
        )
        return (
            f"pbkdf2_{self.HASH_NAME}$"
            f"{self.HASH_ITERATIONS}$"
            f"{salt.hex()}$"
            f"{digest.hex()}"
        )

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$", 3)
            hash_name = algorithm.replace("pbkdf2_", "", 1)
            expected = bytes.fromhex(digest_hex)
            salt = bytes.fromhex(salt_hex)
            computed = hashlib.pbkdf2_hmac(
                hash_name,
                password.encode("utf-8"),
                salt,
                int(iterations),
            )
            return hmac.compare_digest(computed, expected)
        except (ValueError, TypeError):
            return False


auth_service = AuthService()
