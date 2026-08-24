"""Usuarios del sistema y sus roles."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import UUIDType, enum_texto
from app.models.base import AuditMixin, generate_uuid


class RolUsuario(StrEnum):
    """
    Los tres roles del local.

    - `admin`: el dueño. Toca todo, incluidos precios, usuarios y parámetros.
    - `encargado`: maneja el local. Cierra caja, autoriza ajustes de stock,
      devoluciones y descuentos por encima del tope del vendedor.
    - `vendedor`: mostrador. Vende, consulta catálogo y existencias.
    """

    admin = "ADMIN"
    encargado = "ENCARGADO"
    vendedor = "VENDEDOR"


class Usuario(Base, AuditMixin):
    """Una persona con acceso al sistema."""

    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        enum_texto(RolUsuario, 20), nullable=False, index=True
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ultimo_ingreso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Usuario {self.email} ({self.rol})>"
