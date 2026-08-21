"""Modelos del sistema.

Se importan todos acá para que `Base.metadata` los conozca: Alembic compara
contra ese metadata al autogenerar, y un modelo que nadie importó no aparece
en la migración.
"""

from app.models.audit_log import AuditLog, OperacionAudit
from app.models.base import AuditMixin, TimestampMixin, generate_uuid
from app.models.catalogo import Categoria, Color, CurvaTalle, Marca, Talle
from app.models.precio import Precio
from app.models.producto import Genero, ImagenProducto, Producto, Temporada, Variante
from app.models.sucursal import Sucursal, TipoSucursal
from app.models.usuario import RolUsuario, Usuario

__all__ = [
    "AuditLog",
    "AuditMixin",
    "Categoria",
    "Color",
    "CurvaTalle",
    "Genero",
    "ImagenProducto",
    "Marca",
    "OperacionAudit",
    "Precio",
    "Producto",
    "RolUsuario",
    "Sucursal",
    "Talle",
    "Temporada",
    "TimestampMixin",
    "TipoSucursal",
    "Usuario",
    "Variante",
    "generate_uuid",
]
