"""Ventas del mostrador y el catálogo de artículos."""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.deps import CurrentUser, DbSession, EncargadoUser
from app.models.caja import TipoMovimientoCaja
from app.models.usuario import Usuario
from app.models.venta import Articulo, EstadoVenta, LineaVenta, Venta
from app.schemas.venta import (
    AnulacionVenta,
    ArticuloCreate,
    ArticuloOut,
    ArticuloUpdate,
    CobroOut,
    LineaVentaOut,
    VentaCreate,
    VentaEnLista,
    VentaOut,
)
from app.services import venta_service
from app.services.venta_service import LineaPedida, PagoPedido

articulos_router = APIRouter(prefix="/articulos", tags=["ventas"])
router = APIRouter(prefix="/ventas", tags=["ventas"])


# ── Artículos ─────────────────────────────────────────────────────────────────


@articulos_router.get("", response_model=list[ArticuloOut])
async def listar_articulos(
    db: DbSession,
    _usuario: CurrentUser,
    buscar: str | None = None,
    solo_activos: bool = True,
) -> list[Articulo]:
    """Lista el catálogo. Lo consulta cualquiera: es lo que se usa al vender."""
    consulta = select(Articulo).order_by(Articulo.nombre)
    if solo_activos:
        consulta = consulta.where(Articulo.activo.is_(True))
    if buscar:
        patron = f"%{buscar.strip()}%"
        consulta = consulta.where(
            or_(Articulo.nombre.ilike(patron), Articulo.categoria.ilike(patron))
        )
    resultado = await db.execute(consulta)
    return list(resultado.scalars().all())


@articulos_router.post(
    "", response_model=ArticuloOut, status_code=status.HTTP_201_CREATED
)
async def crear_articulo(
    datos: ArticuloCreate, db: DbSession, _encargado: EncargadoUser
) -> Articulo:
    """Da de alta un artículo del catálogo."""
    articulo = Articulo(
        nombre=datos.nombre.strip(),
        categoria=(datos.categoria or "").strip() or None,
        precio=datos.precio,
        activo=True,
    )
    db.add(articulo)
    try:
        await db.flush()
    except IntegrityError as err:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un artículo con ese nombre"
        ) from err
    return articulo


@articulos_router.patch("/{articulo_id}", response_model=ArticuloOut)
async def modificar_articulo(
    articulo_id: uuid.UUID,
    datos: ArticuloUpdate,
    db: DbSession,
    _encargado: EncargadoUser,
) -> Articulo:
    """Modifica un artículo.

    Cambiar el precio no toca ninguna venta anterior: cada línea guardó el
    precio con el que se vendió.
    """
    articulo = await db.get(Articulo, articulo_id)
    if articulo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artículo no encontrado")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        if campo in {"nombre", "categoria"} and isinstance(valor, str):
            valor = valor.strip() or None
        setattr(articulo, campo, valor)
    try:
        await db.flush()
    except IntegrityError as err:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un artículo con ese nombre"
        ) from err
    return articulo


# ── Armado de la respuesta ────────────────────────────────────────────────────


async def _nombres_de(db: DbSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Los nombres de quienes registraron o anularon, en una consulta."""
    if not ids:
        return {}
    resultado = await db.execute(
        select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids))
    )
    return {fila[0]: fila[1] for fila in resultado.all()}


async def _a_salida(db: DbSession, venta: Venta) -> VentaOut:
    """Arma la venta con sus líneas y con cómo se pagó."""
    nombres = await _nombres_de(
        db, {i for i in (venta.registrada_por, venta.anulada_por) if i is not None}
    )
    cobros = await venta_service.cobros_de(db, venta.id)
    return VentaOut(
        id=venta.id,
        numero=venta.numero,
        estado=venta.estado,
        fecha=venta.fecha,
        registrada_por=venta.registrada_por,
        registrada_por_nombre=nombres.get(venta.registrada_por),
        sesion_caja_id=venta.sesion_caja_id,
        subtotal=venta.subtotal,
        descuento=venta.descuento,
        total=venta.total,
        observaciones=venta.observaciones,
        anulada_por_nombre=(
            nombres.get(venta.anulada_por) if venta.anulada_por else None
        ),
        fecha_anulacion=venta.fecha_anulacion,
        motivo_anulacion=venta.motivo_anulacion,
        lineas=[LineaVentaOut.model_validate(linea) for linea in venta.lineas],
        cobros=[
            CobroOut(
                medio_pago_id=cobro.medio_pago_id,
                medio_pago=cobro.medio_pago.nombre,
                importe=cobro.importe,
                es_reversion=cobro.tipo is not TipoMovimientoCaja.cobro,
            )
            for cobro in cobros
        ],
    )


async def _traer_venta(db: DbSession, venta_id: uuid.UUID) -> Venta:
    """Trae la venta con sus líneas cargadas, o corta con 404."""
    resultado = await db.execute(
        select(Venta)
        .options(selectinload(Venta.lineas))
        .where(Venta.id == venta_id)
        .execution_options(populate_existing=True)
    )
    venta = resultado.scalar_one_or_none()
    if venta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    return venta


# ── Ventas ────────────────────────────────────────────────────────────────────


@router.post("", response_model=VentaOut, status_code=status.HTTP_201_CREATED)
async def registrar_venta(
    datos: VentaCreate, db: DbSession, usuario: CurrentUser
) -> VentaOut:
    """Registra una venta y mete sus cobros en la caja abierta."""
    try:
        venta = await venta_service.registrar(
            db,
            usuario_id=usuario.id,
            lineas=[
                LineaPedida(
                    cantidad=linea.cantidad,
                    precio_unitario=linea.precio_unitario,
                    descuento=linea.descuento,
                    articulo_id=linea.articulo_id,
                    descripcion=linea.descripcion,
                    talle=linea.talle,
                )
                for linea in datos.lineas
            ],
            pagos=[
                PagoPedido(medio_pago_id=pago.medio_pago_id, importe=pago.importe)
                for pago in datos.pagos
            ],
            descuento=datos.descuento,
            observaciones=datos.observaciones,
        )
    except venta_service.SinCajaAbiertaError as err:
        raise HTTPException(status.HTTP_409_CONFLICT, str(err)) from err
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err

    return await _a_salida(db, await _traer_venta(db, venta.id))


@router.get("", response_model=list[VentaEnLista])
async def listar_ventas(
    db: DbSession,
    _usuario: CurrentUser,
    buscar: str | None = None,
    solo_anuladas: bool = False,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[VentaEnLista]:
    """Las ventas, de la más nueva a la más vieja."""
    consulta = (
        select(Venta)
        .options(selectinload(Venta.lineas))
        .order_by(Venta.numero.desc())
        .limit(limite)
    )
    if solo_anuladas:
        consulta = consulta.where(Venta.estado == EstadoVenta.anulada)
    if buscar:
        texto = buscar.strip()
        # Se busca por número de venta o por lo que dice alguna de sus líneas:
        # en el mostrador se busca "la campera de ayer", no un identificador.
        condiciones: list[ColumnElement[bool]] = [
            Venta.id.in_(
                select(LineaVenta.venta_id).where(
                    LineaVenta.descripcion.ilike(f"%{texto}%")
                )
            )
        ]
        if texto.lstrip("#").isdigit():
            condiciones.append(Venta.numero == int(texto.lstrip("#")))
        consulta = consulta.where(or_(*condiciones))

    ventas = list((await db.execute(consulta)).scalars().all())
    nombres = await _nombres_de(db, {v.registrada_por for v in ventas})
    return [
        VentaEnLista(
            id=venta.id,
            numero=venta.numero,
            estado=venta.estado,
            fecha=venta.fecha,
            registrada_por_nombre=nombres.get(venta.registrada_por),
            cantidad_articulos=sum(linea.cantidad for linea in venta.lineas),
            total=venta.total,
        )
        for venta in ventas
    ]


@router.get("/{venta_id}", response_model=VentaOut)
async def leer_venta(
    venta_id: uuid.UUID, db: DbSession, _usuario: CurrentUser
) -> VentaOut:
    """Una venta con sus líneas y cómo se pagó."""
    return await _a_salida(db, await _traer_venta(db, venta_id))


@router.post("/{venta_id}/anulacion", response_model=VentaOut)
async def anular_venta(
    venta_id: uuid.UUID, datos: AnulacionVenta, db: DbSession, usuario: CurrentUser
) -> VentaOut:
    """Anula una venta y devuelve la plata a la caja abierta.

    La venta no se borra: queda marcada como anulada, con quién la anuló y por
    qué. Las reversiones van a la caja de ahora, no a la de la venta original,
    que puede estar cerrada con su arqueo ya congelado.
    """
    venta = await _traer_venta(db, venta_id)
    try:
        await venta_service.anular(
            db, venta=venta, usuario_id=usuario.id, motivo=datos.motivo
        )
    except venta_service.VentaYaAnuladaError as err:
        raise HTTPException(status.HTTP_409_CONFLICT, str(err)) from err
    except venta_service.SinCajaAbiertaError as err:
        raise HTTPException(status.HTTP_409_CONFLICT, str(err)) from err
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err

    return await _a_salida(db, await _traer_venta(db, venta_id))
