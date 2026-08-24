"""Esquemas de usuarios."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.usuario import RolUsuario


class UsuarioCreate(BaseModel):
    """Alta de usuario. La contraseña llega en claro y se hashea al guardar."""

    nombre: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    rol: RolUsuario


class UsuarioUpdate(BaseModel):
    """Modificación de usuario. La contraseña se cambia por separado."""

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    rol: RolUsuario | None = None
    activo: bool | None = None


class UsuarioOut(BaseModel):
    """Usuario como lo devuelve la API. Nunca incluye el hash."""

    id: uuid.UUID
    nombre: str
    email: EmailStr
    rol: RolUsuario
    activo: bool
    ultimo_ingreso: datetime | None

    model_config = {"from_attributes": True}
