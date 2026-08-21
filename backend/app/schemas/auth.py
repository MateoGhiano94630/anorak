"""Esquemas de entrada y salida del circuito de ingreso."""

import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credenciales que manda el formulario de ingreso."""

    email: EmailStr
    password: str


class UsuarioActual(BaseModel):
    """Datos del usuario que la interfaz necesita para armar el menú."""

    id: uuid.UUID
    nombre: str
    email: EmailStr
    rol: str
    sucursal_id: uuid.UUID | None
    sucursal_nombre: str | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Respuesta del ingreso: el token y quién es el que entró."""

    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioActual


class CambioPassword(BaseModel):
    """Cambio de la contraseña propia."""

    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=128)


class CambioPasswordOk(BaseModel):
    """Confirmación del cambio de contraseña."""

    mensaje: str = "Contraseña actualizada"
