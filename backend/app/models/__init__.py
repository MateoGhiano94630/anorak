"""Modelos del sistema.

Se importan todos acá para que `Base.metadata` los conozca: Alembic compara
contra ese metadata al autogenerar, y un modelo que nadie importó no aparece
en la migración.
"""

from app.models.audit_log import AuditLog, OperacionAudit
from app.models.base import AuditMixin, TimestampMixin, generate_uuid
from app.models.caja import (
    EstadoSesionCaja,
    MedioPago,
    MovimientoCaja,
    SesionCaja,
    TipoDocumentoCaja,
    TipoMedioPago,
    TipoMovimientoCaja,
)
from app.models.usuario import RolUsuario, Usuario

__all__ = [
    "AuditLog",
    "AuditMixin",
    "EstadoSesionCaja",
    "MedioPago",
    "MovimientoCaja",
    "OperacionAudit",
    "RolUsuario",
    "SesionCaja",
    "TimestampMixin",
    "TipoDocumentoCaja",
    "TipoMedioPago",
    "TipoMovimientoCaja",
    "Usuario",
    "generate_uuid",
]
