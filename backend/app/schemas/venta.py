"""
Esquemas de ventas y del catálogo de artículos.

Los importes viajan como texto en el JSON: los decimales de JavaScript no
representan exactamente los centavos, y esa diferencia aparece sumada en un
cierre de caja.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.venta import EstadoVenta

# ── Artículos ─────────────────────────────────────────────────────────────────


class ArticuloCreate(BaseModel):
    """Alta de un artículo del catálogo."""

    nombre: str = Field(min_length=1, max_length=120)
    categoria: str | None = Field(default=None, max_length=50)
    precio: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class ArticuloUpdate(BaseModel):
    """Modificación de un artículo."""

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    categoria: str | None = Field(default=None, max_length=50)
    precio: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    activo: bool | None = None


class ArticuloOut(BaseModel):
    """Un artículo como lo devuelve la API."""

    id: uuid.UUID
    nombre: str
    categoria: str | None
    precio: Decimal
    activo: bool

    model_config = {"from_attributes": True}


# ── Ventas ────────────────────────────────────────────────────────────────────


class LineaVentaCreate(BaseModel):
    """Una línea de la venta.

    Puede salir del catálogo (`articulo_id`) o escribirse a mano
    (`descripcion`). Una de las dos tiene que venir: sin eso, la línea no dice
    qué se vendió.
    """

    articulo_id: uuid.UUID | None = None
    descripcion: str | None = Field(default=None, max_length=200)
    talle: str | None = Field(default=None, max_length=15)
    cantidad: int = Field(gt=0, le=9999)
    precio_unitario: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    descuento: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2
    )

    @model_validator(mode="after")
    def _dice_que_se_vendio(self) -> "LineaVentaCreate":
        """Rechaza una línea que no dice qué se vendió."""
        if self.articulo_id is None and not (self.descripcion or "").strip():
            raise ValueError("La línea tiene que decir qué se vendió")
        return self


class PagoCreate(BaseModel):
    """Un cobro de la venta. Varios cobros son varios medios de pago."""

    medio_pago_id: uuid.UUID
    importe: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class VentaCreate(BaseModel):
    """Una venta del mostrador."""

    lineas: list[LineaVentaCreate] = Field(min_length=1)
    pagos: list[PagoCreate] = Field(min_length=1)
    # Descuento sobre el total, además de los de cada línea.
    descuento: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2
    )
    observaciones: str | None = None


class AnulacionVenta(BaseModel):
    """La anulación de una venta."""

    motivo: str = Field(min_length=1, max_length=200)


class LineaVentaOut(BaseModel):
    """Una línea de la venta, con lo que quedó escrito en ella."""

    id: uuid.UUID
    numero: int
    articulo_id: uuid.UUID | None
    descripcion: str
    talle: str | None
    cantidad: int
    precio_unitario: Decimal
    descuento: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class CobroOut(BaseModel):
    """Cómo se pagó la venta. Sale de los movimientos de caja."""

    medio_pago_id: uuid.UUID
    medio_pago: str
    importe: Decimal
    # Negativo cuando es la reversión de una anulación.
    es_reversion: bool


class VentaOut(BaseModel):
    """Una venta completa."""

    id: uuid.UUID
    numero: int
    estado: EstadoVenta
    fecha: datetime
    registrada_por: uuid.UUID
    registrada_por_nombre: str | None
    sesion_caja_id: uuid.UUID
    subtotal: Decimal
    descuento: Decimal
    total: Decimal
    observaciones: str | None
    anulada_por_nombre: str | None
    fecha_anulacion: datetime | None
    motivo_anulacion: str | None
    lineas: list[LineaVentaOut]
    cobros: list[CobroOut]


class VentaEnLista(BaseModel):
    """Una venta en el listado, sin el detalle de sus líneas."""

    id: uuid.UUID
    numero: int
    estado: EstadoVenta
    fecha: datetime
    registrada_por_nombre: str | None
    cantidad_articulos: int
    total: Decimal
