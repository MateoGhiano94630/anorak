"""
Esquemas de caja.

Los importes viajan como texto en el JSON, no como número decimal de
JavaScript: `12345.67` en punto flotante no es exactamente 12345.67, y esa
diferencia aparece sumada en un cierre de caja. Pydantic serializa `Decimal`
como texto, y el frontend lo formatea sin convertirlo a número.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.caja import (
    EstadoSesionCaja,
    TipoDocumentoCaja,
    TipoMedioPago,
    TipoMovimientoCaja,
)

# ── Medios de pago ────────────────────────────────────────────────────────────


class MedioPagoCreate(BaseModel):
    """Alta de un medio de pago."""

    nombre: str = Field(min_length=1, max_length=50)
    tipo: TipoMedioPago
    afecta_efectivo: bool = False
    comision_porcentaje: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    dias_acreditacion: int | None = Field(default=None, ge=0, le=365)
    orden: int = 0


class MedioPagoUpdate(BaseModel):
    """Modificación de un medio de pago."""

    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    comision_porcentaje: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    dias_acreditacion: int | None = Field(default=None, ge=0, le=365)
    orden: int | None = None
    activo: bool | None = None


class MedioPagoOut(BaseModel):
    """Un medio de pago como lo devuelve la API."""

    id: uuid.UUID
    nombre: str
    tipo: TipoMedioPago
    afecta_efectivo: bool
    comision_porcentaje: Decimal | None
    dias_acreditacion: int | None
    orden: int
    activo: bool

    model_config = {"from_attributes": True}


# ── Caja ──────────────────────────────────────────────────────────────────────


class AperturaCaja(BaseModel):
    """El fondo con el que arranca el cajón."""

    monto_inicial: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class MovimientoCajaCreate(BaseModel):
    """Un ingreso, un retiro o un gasto cargado a mano.

    Los tres son en efectivo: son lo que entra o sale del cajón. Un gasto
    pagado por transferencia no toca la caja, así que no se registra acá.

    El importe se carga siempre en positivo y el sistema le pone el signo
    según el tipo. Pedirle a quien atiende que escriba un número negativo para
    sacar plata es una forma de que un día cargue el signo al revés.
    """

    tipo: TipoMovimientoCaja
    importe: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    concepto: str = Field(min_length=1, max_length=200)
    comprobante: str | None = Field(default=None, max_length=50)


class CierreCaja(BaseModel):
    """El arqueo: lo que se contó y lo que se deja para mañana."""

    efectivo_declarado: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    fondo_a_dejar: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    # Obligatorio solo si el arqueo no coincide. Lo valida el servicio, que es
    # el único que sabe cuánto se esperaba.
    motivo_diferencia: str | None = Field(default=None, max_length=200)
    observaciones: str | None = None


class MovimientoCajaOut(BaseModel):
    """Un movimiento del historial de la sesión."""

    id: uuid.UUID
    # El renglón dentro de la sesión. Es lo que da el orden del libro.
    numero: int
    tipo: TipoMovimientoCaja
    medio_pago_id: uuid.UUID
    medio_pago: str
    importe: Decimal
    concepto: str | None
    comprobante: str | None
    documento_tipo: TipoDocumentoCaja | None
    documento_id: uuid.UUID | None
    fecha: datetime
    usuario_id: uuid.UUID | None


class TotalPorMedio(BaseModel):
    """Lo cobrado con un medio de pago durante la sesión."""

    medio_pago_id: uuid.UUID
    medio_pago: str
    total: Decimal


class SesionCajaOut(BaseModel):
    """Una sesión de caja.

    Mientras está abierta, `efectivo_esperado` y `diferencia` vienen nulos y
    `totales_por_medio` **no incluye el efectivo**: el arqueo es a ciegas, y
    ver el número antes de contar lo convierte en un trámite.
    """

    id: uuid.UUID
    estado: EstadoSesionCaja
    fecha_apertura: datetime
    abierta_por: uuid.UUID
    abierta_por_nombre: str | None
    monto_inicial: Decimal
    fecha_cierre: datetime | None
    cerrada_por: uuid.UUID | None
    cerrada_por_nombre: str | None
    efectivo_declarado: Decimal | None
    efectivo_esperado: Decimal | None
    diferencia: Decimal | None
    motivo_diferencia: str | None
    monto_retirado: Decimal | None
    fondo_dejado: Decimal | None
    observaciones: str | None
    totales_por_medio: list[TotalPorMedio]
    movimientos: list[MovimientoCajaOut]


class SesionEnLista(BaseModel):
    """Una sesión en el historial, sin el detalle de sus movimientos."""

    id: uuid.UUID
    estado: EstadoSesionCaja
    fecha_apertura: datetime
    abierta_por_nombre: str | None
    fecha_cierre: datetime | None
    cerrada_por_nombre: str | None
    monto_inicial: Decimal
    efectivo_declarado: Decimal | None
    efectivo_esperado: Decimal | None
    diferencia: Decimal | None
    monto_retirado: Decimal | None
