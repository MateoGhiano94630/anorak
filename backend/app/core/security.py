"""Hash de contraseñas y firma de JWT."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hashea una contraseña con bcrypt.

    Se usa `bcrypt` directo y nunca `passlib`: passlib 1.7.4 lee
    `bcrypt.__about__.__version__`, que bcrypt 5.x ya no expone, y falla al
    importar. La API de bcrypt es de tres funciones — no hace falta la capa.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash."""
    return bool(
        bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    )


def create_access_token(data: dict[str, Any]) -> str:
    """Crea un JWT firmado con la expiración configurada."""
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    return str(jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256"))


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un JWT. Lanza `JWTError` si es inválido o venció."""
    resultado: dict[str, Any] = jwt.decode(
        token, settings.jwt_secret_key, algorithms=["HS256"]
    )
    return resultado
