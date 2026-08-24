"""
Apertura, movimientos y cierre de la caja.

Todo peso que entra o sale pasa por `registrar_movimiento`. Es el único lugar
que escribe en `movimiento_caja`, por el mismo motivo por el que la auditoría
es automática: si cada módulo anotara por su cuenta, alcanzaría con que uno se
olvide para que el arqueo quede sin explicación.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caja import (
    EstadoSesionCaja,
    MedioPago,
    MovimientoCaja,
    SesionCaja,
    TipoDocumentoCaja,
    TipoMedioPago,
    TipoMovimientoCaja,
)

CERO = Decimal("0.00")

# Lo que carga una persona a mano tiene que decir por qué. El resto lo genera
# el propio circuito y ya se explica solo por su tipo.
_TIPOS_QUE_EXIGEN_CONCEPTO = {
    TipoMovimientoCaja.ingreso,
    TipoMovimientoCaja.retiro,
    TipoMovimientoCaja.gasto,
}


class CajaCerradaError(RuntimeError):
    """No hay ninguna caja abierta, o la sesión indicada ya se cerró."""


class CajaYaAbiertaError(RuntimeError):
    """Ya hay una sesión abierta."""

    def __init__(self, sesion: SesionCaja) -> None:
        self.sesion = sesion
        super().__init__("Ya hay una caja abierta")


class EfectivoInsuficienteError(RuntimeError):
    """La salida dejaría el cajón en negativo.

    A propósito **no** dice cuánto hay: el arqueo es a ciegas, y el mensaje de
    error no puede ser la forma de averiguar el saldo antes de contar.
    """


async def sesion_abierta(db: AsyncSession) -> SesionCaja | None:
    """La sesión abierta, si hay alguna."""
    resultado = await db.execute(
        select(SesionCaja).where(SesionCaja.estado == EstadoSesionCaja.abierta)
    )
    return resultado.scalar_one_or_none()


async def medio_efectivo(db: AsyncSession) -> MedioPago:
    """El medio de pago que representa el efectivo."""
    resultado = await db.execute(
        select(MedioPago).where(MedioPago.tipo == TipoMedioPago.efectivo)
    )
    medio = resultado.scalars().first()
    if medio is None:
        raise RuntimeError(
            "No hay un medio de pago en efectivo cargado. Sin eso la caja no "
            "puede abrirse."
        )
    return medio


async def efectivo_en_caja(db: AsyncSession, sesion_id: uuid.UUID) -> Decimal:
    """Cuánto efectivo debería haber en el cajón, según los movimientos.

    Este número **no se le muestra a quien cierra** hasta que declara lo que
    contó: si lo viera antes, la tentación es tipearlo y el arqueo deja de
    medir nada.
    """
    resultado = await db.execute(
        select(func.coalesce(func.sum(MovimientoCaja.importe), CERO))
        .join(MedioPago, MedioPago.id == MovimientoCaja.medio_pago_id)
        .where(
            MovimientoCaja.sesion_id == sesion_id,
            MedioPago.afecta_efectivo.is_(True),
        )
    )
    return Decimal(resultado.scalar_one())


async def totales_por_medio(
    db: AsyncSession, sesion_id: uuid.UUID
) -> dict[uuid.UUID, Decimal]:
    """Lo cobrado por cada medio de pago en la sesión."""
    resultado = await db.execute(
        select(
            MovimientoCaja.medio_pago_id,
            func.coalesce(func.sum(MovimientoCaja.importe), CERO),
        )
        .where(MovimientoCaja.sesion_id == sesion_id)
        .group_by(MovimientoCaja.medio_pago_id)
    )
    return {fila[0]: Decimal(fila[1]) for fila in resultado.all()}


async def abrir(
    db: AsyncSession, *, usuario_id: uuid.UUID, monto_inicial: Decimal
) -> SesionCaja:
    """Abre la caja con el fondo con el que arranca el cajón."""
    abierta = await sesion_abierta(db)
    if abierta is not None:
        raise CajaYaAbiertaError(abierta)

    sesion = SesionCaja(
        estado=EstadoSesionCaja.abierta,
        fecha_apertura=datetime.now(UTC),
        abierta_por=usuario_id,
        monto_inicial=monto_inicial,
    )
    db.add(sesion)
    await db.flush()

    # La apertura es un movimiento más. Así el efectivo del cajón es siempre
    # la suma de los movimientos, sin tener que acordarse de sumarle aparte el
    # monto inicial.
    await registrar_movimiento(
        db,
        sesion=sesion,
        tipo=TipoMovimientoCaja.apertura,
        importe=monto_inicial,
        medio_pago=await medio_efectivo(db),
        concepto="Fondo inicial",
    )
    return sesion


async def registrar_movimiento(
    db: AsyncSession,
    *,
    sesion: SesionCaja,
    tipo: TipoMovimientoCaja,
    importe: Decimal,
    medio_pago: MedioPago,
    concepto: str | None = None,
    comprobante: str | None = None,
    documento_tipo: TipoDocumentoCaja | None = None,
    documento_id: uuid.UUID | None = None,
    permitir_negativo: bool = False,
) -> MovimientoCaja:
    """Anota un movimiento de caja.

    `importe` va con signo: positivo entra, negativo sale.

    Una salida que dejaría el cajón en negativo se rechaza. Es una acción que
    está por pasar —se está por sacar plata que no hay—, así que frenarla es
    lo correcto; distinto del arqueo, que refleja algo que ya pasó y por eso
    nunca se rechaza (para eso está `permitir_negativo`).
    """
    if sesion.estado is not EstadoSesionCaja.abierta:
        raise CajaCerradaError("La caja ya está cerrada")
    if importe == CERO:
        raise ValueError("Un movimiento de cero pesos no registra nada")
    if tipo in _TIPOS_QUE_EXIGEN_CONCEPTO and not (concepto or "").strip():
        raise ValueError("Falta el motivo del movimiento")

    if importe < CERO and medio_pago.afecta_efectivo and not permitir_negativo:
        disponible = await efectivo_en_caja(db, sesion.id)
        if disponible + importe < CERO:
            raise EfectivoInsuficienteError("No hay tanto efectivo en la caja")

    siguiente = await db.execute(
        select(func.coalesce(func.max(MovimientoCaja.numero), 0) + 1).where(
            MovimientoCaja.sesion_id == sesion.id
        )
    )
    movimiento = MovimientoCaja(
        sesion_id=sesion.id,
        numero=int(siguiente.scalar_one()),
        tipo=tipo,
        medio_pago_id=medio_pago.id,
        importe=importe,
        concepto=concepto,
        comprobante=comprobante,
        documento_tipo=documento_tipo,
        documento_id=documento_id,
    )
    db.add(movimiento)
    await db.flush()
    return movimiento


async def cerrar(
    db: AsyncSession,
    *,
    sesion: SesionCaja,
    usuario_id: uuid.UUID,
    efectivo_declarado: Decimal,
    fondo_a_dejar: Decimal,
    motivo_diferencia: str | None = None,
    observaciones: str | None = None,
) -> SesionCaja:
    """Cierra la caja: congela el arqueo, anota la diferencia y el retiro.

    El orden importa y deja el libro cuadrado:

    1. Se calcula lo esperado sumando los movimientos en efectivo.
    2. Si lo contado no coincide, la diferencia se anota **como movimiento**.
       Después de eso, la suma da lo que realmente hay en el cajón. Un faltante
       que no se anota deja el libro diciendo una cosa y el cajón otra.
    3. Se retira lo que sobra del fondo, también como movimiento.

    Al terminar, la suma de los movimientos en efectivo es exactamente el
    fondo que quedó. Eso es comprobable, y hay un test que lo comprueba.
    """
    if sesion.estado is not EstadoSesionCaja.abierta:
        raise CajaCerradaError("La caja ya está cerrada")
    if efectivo_declarado < CERO:
        raise ValueError("El efectivo contado no puede ser negativo")
    if fondo_a_dejar < CERO:
        raise ValueError("El fondo a dejar no puede ser negativo")
    if fondo_a_dejar > efectivo_declarado:
        raise ValueError("No se puede dejar en el cajón más de lo que hay")

    esperado = await efectivo_en_caja(db, sesion.id)
    diferencia = efectivo_declarado - esperado
    if diferencia != CERO and not (motivo_diferencia or "").strip():
        raise ValueError("El arqueo no coincide: hace falta explicar la diferencia")

    efectivo = await medio_efectivo(db)

    if diferencia != CERO:
        await registrar_movimiento(
            db,
            sesion=sesion,
            tipo=TipoMovimientoCaja.diferencia,
            importe=diferencia,
            medio_pago=efectivo,
            concepto=motivo_diferencia,
            # La diferencia refleja lo que ya se contó. Si falta plata, la
            # plata ya no está: rechazar el movimiento no la trae de vuelta.
            permitir_negativo=True,
        )

    retirado = efectivo_declarado - fondo_a_dejar
    if retirado > CERO:
        await registrar_movimiento(
            db,
            sesion=sesion,
            tipo=TipoMovimientoCaja.cierre,
            importe=-retirado,
            medio_pago=efectivo,
            concepto="Retiro del cierre",
        )

    sesion.estado = EstadoSesionCaja.cerrada
    sesion.fecha_cierre = datetime.now(UTC)
    sesion.cerrada_por = usuario_id
    sesion.efectivo_declarado = efectivo_declarado
    sesion.efectivo_esperado = esperado
    sesion.diferencia = diferencia
    sesion.motivo_diferencia = motivo_diferencia
    sesion.monto_retirado = retirado
    sesion.fondo_dejado = fondo_a_dejar
    sesion.observaciones = observaciones
    await db.flush()
    return sesion
