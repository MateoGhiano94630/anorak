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
from app.models.venta import Articulo, EstadoVenta, LineaVenta, Venta

__all__ = [
    "Articulo",
    "AuditLog",
    "AuditMixin",
    "EstadoSesionCaja",
    "EstadoVenta",
    "LineaVenta",
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
    "Venta",
    "generate_uuid",
]
