"""Cambio y consulta de precios."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.precio import Precio


async def precio_vigente(db: AsyncSession, variante_id: uuid.UUID) -> Precio | None:
    """Devuelve el precio que rige hoy para una variante, o None si no tiene.

    Una variante recién cargada no tiene precio: primero entra al catálogo y
    después se le pone. El punto de venta se niega a vender una variante sin
    precio, en vez de tomarla como si valiera cero.
    """
    resultado = await db.execute(
        select(Precio).where(
            Precio.variante_id == variante_id, Precio.vigente_hasta.is_(None)
        )
    )
    return resultado.scalar_one_or_none()


async def precios_vigentes(
    db: AsyncSession, variante_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Precio]:
    """Los precios vigentes de varias variantes, en una sola consulta.

    Existe para los listados: pedir el precio de a uno dentro de un bucle
    convierte una pantalla de catálogo en cien consultas a la base.
    """
    if not variante_ids:
        return {}
    resultado = await db.execute(
        select(Precio).where(
            Precio.variante_id.in_(variante_ids), Precio.vigente_hasta.is_(None)
        )
    )
    return {precio.variante_id: precio for precio in resultado.scalars().all()}


async def cambiar_precio(
    db: AsyncSession,
    variante_id: uuid.UUID,
    *,
    precio_venta: Decimal,
    costo: Decimal | None = None,
    precio_mayorista: Decimal | None = None,
    motivo: str | None = None,
) -> Precio:
    """Cierra el precio anterior y abre el nuevo.

    El anterior no se modifica ni se borra: se le pone fecha de fin. Así una
    venta de marzo se puede explicar con el precio que regía en marzo, aunque
    hoy sea otro.

    Las dos escrituras van en el mismo flush a propósito. El índice único
    parcial de la tabla no admite dos precios vigentes para la misma variante,
    así que si el cierre del anterior y el alta del nuevo se separaran, un
    error en el medio dejaría a la variante sin precio o con dos.
    """
    ahora = datetime.now(UTC)
    anterior = await precio_vigente(db, variante_id)
    if anterior is not None:
        anterior.vigente_hasta = ahora

    nuevo = Precio(
        variante_id=variante_id,
        costo=costo,
        precio_venta=precio_venta,
        precio_mayorista=precio_mayorista,
        vigente_desde=ahora,
        motivo=motivo,
    )
    db.add(nuevo)
    await db.flush()
    return nuevo


async def historial_de(db: AsyncSession, variante_id: uuid.UUID) -> list[Precio]:
    """Todos los precios que tuvo una variante, del más nuevo al más viejo."""
    resultado = await db.execute(
        select(Precio)
        .where(Precio.variante_id == variante_id)
        .order_by(Precio.vigente_desde.desc())
    )
    return list(resultado.scalars().all())
