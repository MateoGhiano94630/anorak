"""Registro inmutable de toda escritura del sistema."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import FlexibleJSON, UUIDType, enum_texto
from app.models.base import generate_uuid


class OperacionAudit(StrEnum):
    """Tipo de escritura registrada."""

    create = "CREATE"
    update = "UPDATE"
    delete = "DELETE"


class AuditLog(Base):
    """
    Una fila por cada alta, cambio o baja en cualquier tabla.

    No hereda de `AuditMixin` a propósito: si lo hiciera, el listener que
    escribe estas filas se auditaría a sí mismo y entraría en recursión.
    Tampoco se edita ni se borra nunca — es evidencia, no dato de trabajo.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    tabla_afectada: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    registro_id: Mapped[uuid.UUID] = mapped_column(UUIDType, nullable=False, index=True)
    # Texto y no el tipo ENUM de la base: sumar una operación no obliga a
    # migrar un tipo. Ver `enum_texto` en app/core/types.py.
    operacion: Mapped[OperacionAudit] = mapped_column(
        enum_texto(OperacionAudit, 10), nullable=False, index=True
    )
    datos_anteriores: Mapped[dict[str, Any] | None] = mapped_column(
        FlexibleJSON, nullable=True
    )
    datos_nuevos: Mapped[dict[str, Any] | None] = mapped_column(
        FlexibleJSON, nullable=True
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip_origen: Mapped[str | None] = mapped_column(String(45), nullable=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<AuditLog {self.operacion} {self.tabla_afectada}>"
