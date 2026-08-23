"""
Registro de movimientos y mantenimiento de las existencias.

Todo cambio de stock del sistema —venta, ingreso, ajuste, devolución,
transferencia, conteo— pasa por `registrar_movimiento`. Es el único lugar
donde se toca la columna `cantidad` de `stock`.

Está centralizado por la misma razón que la auditoría: si cada módulo
actualizara el saldo por su cuenta, alcanzaría con que uno se olvidara de
escribir el movimiento para que el sistema quedara sin poder explicar de dónde
salió un número. Y la explicación es justamente para lo que sirve.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.stock import MovimientoStock, Stock, TipoDocumento, TipoMovimiento


class StockInsuficienteError(RuntimeError):
    """No hay unidades suficientes para la salida pedida."""

    def __init__(self, disponible: int, pedido: int) -> None:
        self.disponible = disponible
        self.pedido = pedido
        super().__init__(
            f"No hay stock suficiente: quedan {disponible} y se piden {pedido}"
        )


async def _fila_de_stock(
    db: AsyncSession, variante_id: uuid.UUID, sucursal_id: uuid.UUID
) -> Stock:
    """Trae la fila de existencias de esa variante en esa sucursal, o la crea.

    Se pide con bloqueo (`with_for_update`) porque dos cajas pueden vender la
    última unidad al mismo tiempo: sin el bloqueo, las dos leen 1, las dos
    restan, y el stock queda en 0 habiendo vendido dos prendas. En PostgreSQL
    esto emite `FOR UPDATE`; en SQLite, que es donde corren los tests, no
    emite nada porque bloquea la base entera de todos modos.
    """
    resultado = await db.execute(
        select(Stock)
        .where(Stock.variante_id == variante_id, Stock.sucursal_id == sucursal_id)
        .with_for_update()
    )
    fila = resultado.scalar_one_or_none()
    if fila is None:
        # La fila nace al primer movimiento. Crear una en cero para cada
        # combinación de variante y sucursal al dar de alta una prenda llenaría
        # la tabla de ceros que no dicen nada.
        fila = Stock(variante_id=variante_id, sucursal_id=sucursal_id, cantidad=0)
        db.add(fila)
        await db.flush()
    return fila


async def registrar_movimiento(
    db: AsyncSession,
    *,
    variante_id: uuid.UUID,
    sucursal_id: uuid.UUID,
    tipo: TipoMovimiento,
    cantidad: int,
    motivo: str | None = None,
    documento_tipo: TipoDocumento | None = None,
    documento_id: uuid.UUID | None = None,
    permitir_negativo: bool | None = None,
) -> MovimientoStock:
    """Deja el movimiento registrado y actualiza el saldo, en una sola operación.

    `cantidad` va con signo: positivo entra, negativo sale.

    Una salida que dejaría el stock en negativo se rechaza, salvo que el
    parámetro `PERMITIR_STOCK_NEGATIVO` esté encendido. El dueño eligió
    bloquear (20/08/2026); el parámetro existe para que cambiar de opinión sea
    una variable de entorno y no una reescritura del circuito de venta.

    `permitir_negativo` deja forzarlo desde el módulo que llama, para los casos
    en los que el movimiento refleja algo que **ya pasó** en la realidad: un
    conteo físico que encontró menos mercadería de la que el sistema creía
    tener no se puede rechazar, porque la prenda ya no está.
    """
    if cantidad == 0:
        raise ValueError("Un movimiento de cero unidades no registra nada")

    fila = await _fila_de_stock(db, variante_id, sucursal_id)
    resultante = fila.cantidad + cantidad

    if permitir_negativo is None:
        permitir_negativo = settings.permitir_stock_negativo
    if resultante < 0 and not permitir_negativo:
        raise StockInsuficienteError(disponible=fila.cantidad, pedido=abs(cantidad))

    fila.cantidad = resultante
    movimiento = MovimientoStock(
        variante_id=variante_id,
        sucursal_id=sucursal_id,
        tipo=tipo,
        cantidad=cantidad,
        cantidad_resultante=resultante,
        motivo=motivo,
        documento_tipo=documento_tipo,
        documento_id=documento_id,
    )
    db.add(movimiento)
    await db.flush()
    return movimiento


async def ajustar_a(
    db: AsyncSession,
    *,
    variante_id: uuid.UUID,
    sucursal_id: uuid.UUID,
    cantidad_final: int,
    motivo: str,
) -> MovimientoStock | None:
    """Deja el stock en la cantidad indicada, registrando la diferencia.

    Es la operación de "conté y hay 7". El movimiento que queda guardado es la
    diferencia, no el número final: lo que hay que poder explicar después es
    cuánto cambió y por qué.

    Devuelve None si no había nada que corregir. Registrar un movimiento de
    cero unidades ensuciaría el historial sin agregar información.
    """
    fila = await _fila_de_stock(db, variante_id, sucursal_id)
    diferencia = cantidad_final - fila.cantidad
    if diferencia == 0:
        return None
    return await registrar_movimiento(
        db,
        variante_id=variante_id,
        sucursal_id=sucursal_id,
        tipo=TipoMovimiento.ajuste,
        cantidad=diferencia,
        motivo=motivo,
        # Un ajuste refleja lo que ya se contó: si hay menos de lo que el
        # sistema creía, la prenda ya no está y rechazarlo no la trae de vuelta.
        permitir_negativo=True,
    )


async def cantidad_actual(
    db: AsyncSession, variante_id: uuid.UUID, sucursal_id: uuid.UUID
) -> int:
    """Cuántas unidades hay ahora, según el saldo guardado."""
    resultado = await db.execute(
        select(Stock.cantidad).where(
            Stock.variante_id == variante_id, Stock.sucursal_id == sucursal_id
        )
    )
    return resultado.scalar_one_or_none() or 0


async def cantidad_por_movimientos(
    db: AsyncSession, variante_id: uuid.UUID, sucursal_id: uuid.UUID
) -> int:
    """Cuántas unidades hay, reconstruido sumando los movimientos.

    Tiene que dar lo mismo que `cantidad_actual`. Que existan las dos formas
    de calcularlo es lo que permite detectar que el saldo se corrompió (D-3).
    """
    resultado = await db.execute(
        select(func.coalesce(func.sum(MovimientoStock.cantidad), 0)).where(
            MovimientoStock.variante_id == variante_id,
            MovimientoStock.sucursal_id == sucursal_id,
        )
    )
    return int(resultado.scalar_one())


async def diferencias_de_control(db: AsyncSession) -> list[tuple[Stock, int]]:
    """Las existencias cuyo saldo no coincide con la suma de sus movimientos.

    Devuelve la fila de stock y lo que dan los movimientos. Si la lista no está
    vacía, hay un error en algún módulo que tocó el stock sin pasar por
    `registrar_movimiento`, y hay que encontrarlo: cada fila de esta lista es
    una prenda cuyo número el local no puede explicar.
    """
    sumas = (
        select(
            MovimientoStock.variante_id.label("variante_id"),
            MovimientoStock.sucursal_id.label("sucursal_id"),
            func.coalesce(func.sum(MovimientoStock.cantidad), 0).label("suma"),
        )
        .group_by(MovimientoStock.variante_id, MovimientoStock.sucursal_id)
        .subquery()
    )
    resultado = await db.execute(
        select(Stock, func.coalesce(sumas.c.suma, 0))
        .outerjoin(
            sumas,
            (Stock.variante_id == sumas.c.variante_id)
            & (Stock.sucursal_id == sumas.c.sucursal_id),
        )
        .where(Stock.cantidad != func.coalesce(sumas.c.suma, 0))
    )
    return [(fila[0], int(fila[1])) for fila in resultado.all()]
