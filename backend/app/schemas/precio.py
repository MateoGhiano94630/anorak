"""Esquemas de precios.

Los importes viajan como texto en el JSON, no como número decimal de
JavaScript: `12345.67` en punto flotante no es exactamente 12345.67, y esa
diferencia aparece sumada en un cierre de caja. Pydantic serializa `Decimal`
como texto, y el frontend lo formatea sin convertirlo a número.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CambioPrecio(BaseModel):
    """Un precio nuevo para una variante."""

    precio_venta: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    costo: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    precio_mayorista: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    motivo: str | None = Field(default=None, max_length=200)


class CambioPrecioMasivo(CambioPrecio):
    """El mismo precio para todas las variantes de un producto.

    Es lo normal en ropa: una remera vale lo mismo en S que en L. Poner el
    precio de a una variante en un producto con cuatro talles y tres colores
    son doce cargas para un solo dato.
    """


class PrecioOut(BaseModel):
    """Un precio del historial."""

    id: uuid.UUID
    variante_id: uuid.UUID
    costo: Decimal | None
    precio_venta: Decimal
    precio_mayorista: Decimal | None
    vigente_desde: datetime
    vigente_hasta: datetime | None
    motivo: str | None

    model_config = {"from_attributes": True}
