import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.Config import settings
from app.db.db_connection import get_db
from app.models.models import Usuario

bearer_scheme = HTTPBearer(auto_error=False)


class TokenService:
    def __init__(self, secret_key: str, expire_minutes: int) -> None:
        self.secret_key = secret_key.encode("utf-8")
        self.expire_minutes = expire_minutes

    def create_access_token(self, usuario: Usuario) -> str:
        payload = {
            "sub": str(usuario.id),
            "username": usuario.username,
            "correo": usuario.correo,
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)).timestamp()),
        }
        payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_encoded = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=")
        signature = hmac.new(self.secret_key, payload_encoded, hashlib.sha256).digest()
        signature_encoded = base64.urlsafe_b64encode(signature).rstrip(b"=")
        return f"{payload_encoded.decode('utf-8')}.{signature_encoded.decode('utf-8')}"

    def decode_token(self, token: str) -> dict:
        try:
            payload_encoded, signature_encoded = token.split(".", 1)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido.") from exc

        expected_signature = hmac.new(
            self.secret_key,
            payload_encoded.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        provided_signature = self._urlsafe_b64decode(signature_encoded)

        if not hmac.compare_digest(expected_signature, provided_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido.")

        payload_bytes = self._urlsafe_b64decode(payload_encoded)
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido.") from exc

        if payload.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado.")

        return payload

    @staticmethod
    def _urlsafe_b64decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(f"{value}{padding}")


token_service = TokenService(
    secret_key=settings.auth_secret_key,
    expire_minutes=settings.auth_token_expire_minutes,
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales requeridas.",
        )

    payload = token_service.decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido.")

    usuario = db.execute(
        select(Usuario).where(
            Usuario.id == UUID(user_id),
            Usuario.is_active.is_(True),
        )
    ).scalar_one_or_none()

    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no autorizado.")

    return usuario


def get_current_active_user(
    usuario: Usuario = Depends(get_current_user),
) -> Usuario:
    if not usuario.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo.")
    return usuario
