"""Esquemas de existencias y movimientos."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.stock import TipoDocumento, TipoMovimiento


class IngresoMercaderia(BaseModel):
    """Mercadería que entra al local."""

    variante_id: uuid.UUID
    sucursal_id: uuid.UUID
    cantidad: int = Field(gt=0)
    motivo: str = Field(min_length=1, max_length=200)


class AjusteStock(BaseModel):
    """Corrección del stock a la cantidad que se contó."""

    variante_id: uuid.UUID
    sucursal_id: uuid.UUID
    cantidad_final: int = Field(ge=0)
    # Obligatorio: un ajuste sin motivo es un número que nadie va a poder
    # explicar dentro de tres meses.
    motivo: str = Field(min_length=1, max_length=200)


class MinimoStock(BaseModel):
    """El punto en el que hay que reponer una prenda."""

    variante_id: uuid.UUID
    sucursal_id: uuid.UUID
    stock_minimo: int = Field(ge=0)


class StockOut(BaseModel):
    """Las existencias de una prenda en una sucursal."""

    variante_id: uuid.UUID
    sucursal_id: uuid.UUID
    sucursal: str
    producto_id: uuid.UUID
    producto: str
    talle: str
    color: str
    sku: str
    cantidad: int
    stock_minimo: int
    bajo_minimo: bool


class MovimientoOut(BaseModel):
    """Un movimiento del historial."""

    id: uuid.UUID
    variante_id: uuid.UUID
    sucursal_id: uuid.UUID
    sucursal: str
    producto: str
    talle: str
    color: str
    sku: str
    tipo: TipoMovimiento
    cantidad: int
    cantidad_resultante: int
    motivo: str | None
    documento_tipo: TipoDocumento | None
    documento_id: uuid.UUID | None
    fecha: datetime
    usuario_id: uuid.UUID | None


class DiferenciaControl(BaseModel):
    """Una prenda cuyo saldo no coincide con la suma de sus movimientos."""

    variante_id: uuid.UUID
    sucursal_id: uuid.UUID
    producto: str
    talle: str
    color: str
    sku: str
    cantidad_guardada: int
    cantidad_por_movimientos: int
