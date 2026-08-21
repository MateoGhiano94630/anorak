"""Modelos del sistema.

Se importan todos acá para que `Base.metadata` los conozca: Alembic compara
contra ese metadata al autogenerar, y un modelo que nadie importó no aparece
en la migración.
"""

from app.models.audit_log import AuditLog, OperacionAudit
from app.models.base import AuditMixin, TimestampMixin, generate_uuid
from app.models.sucursal import Sucursal, TipoSucursal
from app.models.usuario import RolUsuario, Usuario

__all__ = [
    "AuditLog",
    "AuditMixin",
    "OperacionAudit",
    "RolUsuario",
    "Sucursal",
    "TimestampMixin",
    "TipoSucursal",
    "Usuario",
    "generate_uuid",
]
