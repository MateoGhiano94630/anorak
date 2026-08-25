"""
Registro y anulación de ventas.

Una venta toca dos cosas a la vez: crea el documento y mete los cobros en la
caja. Las dos van en el mismo flush, porque una venta cobrada que no aparece
en el arqueo, o un cobro en la caja sin venta que lo explique, son dos formas
distintas de que el cierre del día no cierre.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caja import (
    MedioPago,
    MovimientoCaja,
    SesionCaja,
    TipoDocumentoCaja,
    TipoMovimientoCaja,
)
from app.models.venta import Articulo, EstadoVenta, LineaVenta, Venta
from app.services import caja_service

CERO = Decimal("0.00")


class SinCajaAbiertaError(RuntimeError):
    """No hay una sesión de caja abierta."""


class VentaYaAnuladaError(RuntimeError):
    """La venta ya estaba anulada."""


@dataclass(frozen=True)
class LineaPedida:
    """Una línea tal como la manda el mostrador."""

    cantidad: int
    precio_unitario: Decimal
    descuento: Decimal = CERO
    articulo_id: uuid.UUID | None = None
    descripcion: str | None = None
    talle: str | None = None


@dataclass(frozen=True)
class PagoPedido:
    """Un cobro tal como lo manda el mostrador."""

    medio_pago_id: uuid.UUID
    importe: Decimal


async def _siguiente_numero(db: AsyncSession) -> int:
    """El correlativo de la venta.

    La restricción de unicidad de la columna es la red: si dos cajas
    registran a la vez, la segunda falla en vez de quedar con el mismo número.
    """
    resultado = await db.execute(select(func.coalesce(func.max(Venta.numero), 0) + 1))
    return int(resultado.scalar_one())


async def registrar(
    db: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    lineas: list[LineaPedida],
    pagos: list[PagoPedido],
    descuento: Decimal = CERO,
    observaciones: str | None = None,
) -> Venta:
    """Registra la venta y sus cobros sobre la sesión de caja abierta.

    Valida que lo cobrado sea exactamente el total. Un cobro de menos deja una
    venta a medias que nadie va a reclamar; uno de más descuadra el arqueo. El
    vuelto no se registra: lo que se cobra es el importe de la venta, no lo
    que el cliente puso sobre el mostrador.
    """
    if not lineas:
        raise ValueError("Una venta sin líneas no es una venta")
    if descuento < CERO:
        raise ValueError("El descuento no puede ser negativo")

    sesion = await caja_service.sesion_abierta(db)
    if sesion is None:
        raise SinCajaAbiertaError("La caja está cerrada. Abrila antes de vender.")

    resueltas = await _resolver_lineas(db, lineas)
    subtotal = sum((linea.subtotal for linea in resueltas), start=CERO)
    total = subtotal - descuento
    if total < CERO:
        raise ValueError("El descuento no puede ser mayor que la venta")

    cobrado = sum((pago.importe for pago in pagos), start=CERO)
    if cobrado != total:
        raise ValueError(
            f"Lo cobrado ({cobrado}) no coincide con el total de la venta ({total})"
        )

    venta = Venta(
        numero=await _siguiente_numero(db),
        sesion_caja_id=sesion.id,
        estado=EstadoVenta.registrada,
        fecha=datetime.now(UTC),
        registrada_por=usuario_id,
        subtotal=subtotal,
        descuento=descuento,
        total=total,
        observaciones=observaciones,
    )
    db.add(venta)
    await db.flush()

    for numero, linea in enumerate(resueltas, start=1):
        db.add(
            LineaVenta(
                venta_id=venta.id,
                numero=numero,
                articulo_id=linea.articulo_id,
                descripcion=linea.descripcion,
                talle=linea.talle,
                cantidad=linea.cantidad,
                precio_unitario=linea.precio_unitario,
                descuento=linea.descuento,
                subtotal=linea.subtotal,
            )
        )

    await _cobrar(db, sesion=sesion, venta=venta, pagos=pagos)
    await db.flush()
    return venta


@dataclass(frozen=True)
class _LineaResuelta:
    """Una línea ya con su descripción y su subtotal calculados."""

    articulo_id: uuid.UUID | None
    descripcion: str
    talle: str | None
    cantidad: int
    precio_unitario: Decimal
    descuento: Decimal
    subtotal: Decimal


async def _resolver_lineas(
    db: AsyncSession, lineas: list[LineaPedida]
) -> list[_LineaResuelta]:
    """Completa cada línea con la descripción y el subtotal.

    Una línea puede venir de un artículo del catálogo o escrita a mano. En los
    dos casos la descripción termina copiada en la línea: lo que vale para
    siempre es lo que quedó escrito en el documento.
    """
    ids = {linea.articulo_id for linea in lineas if linea.articulo_id is not None}
    articulos: dict[uuid.UUID, Articulo] = {}
    if ids:
        resultado = await db.execute(select(Articulo).where(Articulo.id.in_(ids)))
        articulos = {articulo.id: articulo for articulo in resultado.scalars().all()}
        faltantes = ids - set(articulos)
        if faltantes:
            raise ValueError("Hay artículos que no existen en el catálogo")

    resueltas: list[_LineaResuelta] = []
    for linea in lineas:
        if linea.cantidad <= 0:
            raise ValueError("La cantidad tiene que ser mayor que cero")
        if linea.precio_unitario < CERO:
            raise ValueError("El precio no puede ser negativo")
        if linea.descuento < CERO:
            raise ValueError("El descuento de una línea no puede ser negativo")

        articulo = (
            articulos[linea.articulo_id] if linea.articulo_id is not None else None
        )
        descripcion = (linea.descripcion or "").strip() or (
            articulo.nombre if articulo is not None else ""
        )
        if not descripcion:
            raise ValueError("Falta decir qué se está vendiendo")

        bruto = linea.precio_unitario * linea.cantidad
        if linea.descuento > bruto:
            raise ValueError(f"El descuento de «{descripcion}» es mayor que la línea")

        resueltas.append(
            _LineaResuelta(
                articulo_id=linea.articulo_id,
                descripcion=descripcion,
                talle=(linea.talle or "").strip() or None,
                cantidad=linea.cantidad,
                precio_unitario=linea.precio_unitario,
                descuento=linea.descuento,
                subtotal=bruto - linea.descuento,
            )
        )
    return resueltas


async def _cobrar(
    db: AsyncSession,
    *,
    sesion: SesionCaja,
    venta: Venta,
    pagos: list[PagoPedido],
) -> None:
    """Mete los cobros de la venta en la caja, uno por medio de pago."""
    medios = await _medios_de(db, [pago.medio_pago_id for pago in pagos])
    for pago in pagos:
        if pago.importe <= CERO:
            raise ValueError("Un cobro tiene que ser mayor que cero")
        await caja_service.registrar_movimiento(
            db,
            sesion=sesion,
            tipo=TipoMovimientoCaja.cobro,
            importe=pago.importe,
            medio_pago=medios[pago.medio_pago_id],
            concepto=f"Venta #{venta.numero}",
            documento_tipo=TipoDocumentoCaja.venta,
            documento_id=venta.id,
        )


async def _medios_de(
    db: AsyncSession, ids: list[uuid.UUID]
) -> dict[uuid.UUID, MedioPago]:
    """Los medios de pago pedidos, o un error si alguno no existe."""
    resultado = await db.execute(select(MedioPago).where(MedioPago.id.in_(set(ids))))
    medios = {medio.id: medio for medio in resultado.scalars().all()}
    if set(ids) - set(medios):
        raise ValueError("Hay medios de pago que no existen")
    inactivos = [m.nombre for m in medios.values() if not m.activo]
    if inactivos:
        raise ValueError(f"El medio de pago «{inactivos[0]}» está dado de baja")
    return medios


async def cobros_de(db: AsyncSession, venta_id: uuid.UUID) -> list[MovimientoCaja]:
    """Los movimientos de caja de una venta, incluidas sus reversiones."""
    resultado = await db.execute(
        select(MovimientoCaja)
        .where(
            MovimientoCaja.documento_tipo == TipoDocumentoCaja.venta,
            MovimientoCaja.documento_id == venta_id,
        )
        .order_by(MovimientoCaja.numero)
    )
    return list(resultado.scalars().all())


async def anular(
    db: AsyncSession, *, venta: Venta, usuario_id: uuid.UUID, motivo: str
) -> Venta:
    """Anula la venta y devuelve la plata a la caja con cobros al revés.

    Las reversiones van a la **sesión abierta ahora**, no a la sesión original
    de la venta. Si fueran a la original y esa caja ya estuviera cerrada, se
    estaría tocando un arqueo congelado: el número que alguien contó y firmó
    dejaría de coincidir con sus movimientos. Es el mismo criterio que usa una
    nota de crédito, que se emite el día que se emite y no se mete en el mes
    ya cerrado.
    """
    if venta.estado is EstadoVenta.anulada:
        raise VentaYaAnuladaError("La venta ya estaba anulada")
    if not motivo.strip():
        raise ValueError("Hace falta decir por qué se anula la venta")

    sesion = await caja_service.sesion_abierta(db)
    if sesion is None:
        raise SinCajaAbiertaError(
            "La caja está cerrada. Abrila antes de anular una venta, porque la "
            "plata tiene que volver a alguna caja."
        )

    for cobro in await cobros_de(db, venta.id):
        # Solo se revierten los cobros originales: si la venta se anulara dos
        # veces, la segunda encontraría también las reversiones y devolvería
        # la plata de nuevo. El estado ya lo impide, y esto es la red.
        if cobro.tipo is not TipoMovimientoCaja.cobro:
            continue
        await caja_service.registrar_movimiento(
            db,
            sesion=sesion,
            tipo=TipoMovimientoCaja.devolucion,
            importe=-cobro.importe,
            medio_pago=cobro.medio_pago,
            concepto=f"Anulación de la venta #{venta.numero}",
            documento_tipo=TipoDocumentoCaja.venta,
            documento_id=venta.id,
            # La anulación devuelve plata que ya se cobró. Si el cajón no
            # alcanza —porque se retiró durante el día— hay que poder hacerla
            # igual: el problema es de dónde sale la plata, no del registro.
            permitir_negativo=True,
        )

    venta.estado = EstadoVenta.anulada
    venta.anulada_por = usuario_id
    venta.fecha_anulacion = datetime.now(UTC)
    venta.motivo_anulacion = motivo.strip()
    await db.flush()
    return venta
