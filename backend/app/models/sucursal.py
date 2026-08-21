"""Sucursales: los puntos donde hay stock, caja y ventas."""

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import UUIDType, enum_texto
from app.models.base import AuditMixin, generate_uuid


class TipoSucursal(StrEnum):
    """Qué es cada punto: uno vende, el otro solo guarda mercadería."""

    local = "LOCAL"
    deposito = "DEPOSITO"


class Sucursal(Base, AuditMixin):
    """
    Un punto físico del negocio.

    Existe desde la primera migración aunque hoy haya un solo local. El
    motivo es que `sucursal_id` viaja en stock, ventas, caja y usuarios:
    agregarlo más adelante obliga a inventar a qué sucursal perteneció cada
    movimiento histórico, y esa respuesta no está en ningún lado.

    Un depósito es una sucursal más, con `tipo = DEPOSITO`: tiene existencias
    y recibe transferencias, pero no abre caja ni emite comprobantes.
    """

    __tablename__ = "sucursal"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    # Código corto para mostrar en listados y prefijar identificadores.
    codigo: Mapped[str] = mapped_column(
        String(10), nullable=False, unique=True, index=True
    )
    tipo: Mapped[TipoSucursal] = mapped_column(
        enum_texto(TipoSucursal, 10), nullable=False, default=TipoSucursal.local
    )
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    localidad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provincia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Punto de venta de ARCA. Cada sucursal factura con el suyo: dos bocas no
    # pueden compartir numeración fiscal. Nulo mientras la facturación esté
    # apagada.
    punto_venta_arca: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Sucursal {self.codigo} {self.nombre}>"
