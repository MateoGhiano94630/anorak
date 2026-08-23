"""Existencias, movimientos, ingresos, ajustes y alertas de mínimo."""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import AdminUser, CurrentUser, DbSession, EncargadoUser
from app.models.producto import Producto, Variante
from app.models.stock import MovimientoStock, Stock, TipoMovimiento
from app.models.sucursal import Sucursal
from app.schemas.stock import (
    AjusteStock,
    DiferenciaControl,
    IngresoMercaderia,
    MinimoStock,
    MovimientoOut,
    StockOut,
)
from app.services import stock_service

router = APIRouter(prefix="/stock", tags=["stock"])

# El producto de la variante no se carga solo: `Variante.producto` no está
# marcada para traerse con la consulta, porque desde la pantalla de catálogo se
# va en el sentido contrario. Acá se pide explícitamente; sin esto, leer el
# nombre del producto intentaría una consulta a mitad de la respuesta y falla.
_CON_PRENDA = selectinload(Stock.variante).selectinload(Variante.producto)
_CON_PRENDA_MOV = selectinload(MovimientoStock.variante).selectinload(Variante.producto)


def _a_salida(fila: Stock) -> StockOut:
    """Arma la fila de existencias con los datos de la prenda."""
    variante = fila.variante
    return StockOut(
        variante_id=fila.variante_id,
        sucursal_id=fila.sucursal_id,
        sucursal=fila.sucursal.nombre,
        producto_id=variante.producto_id,
        producto=variante.producto.nombre,
        talle=variante.talle.valor,
        color=variante.color.nombre,
        sku=variante.sku,
        cantidad=fila.cantidad,
        stock_minimo=fila.stock_minimo,
        # Con mínimo en cero no se controla nada: sería marcar en rojo cada
        # prenda agotada del catálogo, incluidas las que ya no se reponen.
        bajo_minimo=fila.stock_minimo > 0 and fila.cantidad <= fila.stock_minimo,
    )


async def _validar_prenda_y_sucursal(
    db: DbSession, variante_id: uuid.UUID, sucursal_id: uuid.UUID
) -> None:
    """Corta con 400 si la prenda o la sucursal no existen."""
    if await db.get(Variante, variante_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La prenda no existe")
    if await db.get(Sucursal, sucursal_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La sucursal no existe")


@router.get("", response_model=list[StockOut])
async def listar_stock(
    db: DbSession,
    _usuario: CurrentUser,
    sucursal_id: uuid.UUID | None = None,
    producto_id: uuid.UUID | None = None,
    buscar: str | None = None,
    solo_bajo_minimo: bool = False,
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[StockOut]:
    """Lista las existencias, con filtro por sucursal, prenda y texto.

    El filtro por prenda es el que usa la pantalla de una prenda para mostrar
    cuánto hay de cada talle: sin él habría que preguntar de a una variante y
    una remera con cuatro talles y tres colores serían doce consultas.
    """
    consulta = (
        select(Stock)
        .options(_CON_PRENDA)
        .join(Variante, Variante.id == Stock.variante_id)
        .join(Producto, Producto.id == Variante.producto_id)
        .order_by(Producto.nombre, Variante.sku)
        .limit(limite)
    )
    if sucursal_id is not None:
        consulta = consulta.where(Stock.sucursal_id == sucursal_id)
    if producto_id is not None:
        consulta = consulta.where(Variante.producto_id == producto_id)
    if buscar:
        patron = f"%{buscar.strip()}%"
        consulta = consulta.where(
            or_(Producto.nombre.ilike(patron), Variante.sku.ilike(patron))
        )
    if solo_bajo_minimo:
        consulta = consulta.where(
            Stock.stock_minimo > 0, Stock.cantidad <= Stock.stock_minimo
        )
    resultado = await db.execute(consulta)
    return [_a_salida(fila) for fila in resultado.scalars().all()]


@router.get("/alertas", response_model=list[StockOut])
async def listar_alertas(
    db: DbSession, _usuario: CurrentUser, sucursal_id: uuid.UUID | None = None
) -> list[StockOut]:
    """Las prendas que llegaron a su punto de reposición.

    Es la pantalla que se mira antes de hacer un pedido al proveedor: dice qué
    se está por acabar mientras todavía queda algo para vender.
    """
    consulta = (
        select(Stock)
        .options(_CON_PRENDA)
        .where(Stock.stock_minimo > 0, Stock.cantidad <= Stock.stock_minimo)
        .order_by(Stock.cantidad)
    )
    if sucursal_id is not None:
        consulta = consulta.where(Stock.sucursal_id == sucursal_id)
    resultado = await db.execute(consulta)
    return [_a_salida(fila) for fila in resultado.scalars().all()]


@router.get("/movimientos", response_model=list[MovimientoOut])
async def listar_movimientos(
    db: DbSession,
    _usuario: CurrentUser,
    variante_id: uuid.UUID | None = None,
    sucursal_id: uuid.UUID | None = None,
    tipo: TipoMovimiento | None = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MovimientoOut]:
    """El historial de movimientos, del más nuevo al más viejo."""
    consulta = (
        select(MovimientoStock)
        .options(_CON_PRENDA_MOV)
        .order_by(MovimientoStock.created_at.desc())
        .limit(limite)
    )
    if variante_id is not None:
        consulta = consulta.where(MovimientoStock.variante_id == variante_id)
    if sucursal_id is not None:
        consulta = consulta.where(MovimientoStock.sucursal_id == sucursal_id)
    if tipo is not None:
        consulta = consulta.where(MovimientoStock.tipo == tipo)

    resultado = await db.execute(consulta)
    return [
        MovimientoOut(
            id=movimiento.id,
            variante_id=movimiento.variante_id,
            sucursal_id=movimiento.sucursal_id,
            sucursal=movimiento.sucursal.nombre,
            producto=movimiento.variante.producto.nombre,
            talle=movimiento.variante.talle.valor,
            color=movimiento.variante.color.nombre,
            sku=movimiento.variante.sku,
            tipo=movimiento.tipo,
            cantidad=movimiento.cantidad,
            cantidad_resultante=movimiento.cantidad_resultante,
            motivo=movimiento.motivo,
            documento_tipo=movimiento.documento_tipo,
            documento_id=movimiento.documento_id,
            fecha=movimiento.created_at,
            usuario_id=movimiento.created_by,
        )
        for movimiento in resultado.scalars().all()
    ]


@router.get("/control", response_model=list[DiferenciaControl])
async def controlar_existencias(
    db: DbSession, _admin: AdminUser
) -> list[DiferenciaControl]:
    """Compara el saldo guardado contra la suma de los movimientos.

    Tiene que devolver siempre una lista vacía. Si no la devuelve, hay un
    módulo que tocó el stock sin registrar el movimiento, y cada fila es una
    prenda cuyo número el local no puede explicar (D-3).
    """
    diferencias = await stock_service.diferencias_de_control(db)
    salida: list[DiferenciaControl] = []
    for fila, suma in diferencias:
        variante = await db.get(Variante, fila.variante_id)
        assert variante is not None
        producto = await db.get(Producto, variante.producto_id)
        assert producto is not None
        salida.append(
            DiferenciaControl(
                variante_id=fila.variante_id,
                sucursal_id=fila.sucursal_id,
                producto=producto.nombre,
                talle=variante.talle.valor,
                color=variante.color.nombre,
                sku=variante.sku,
                cantidad_guardada=fila.cantidad,
                cantidad_por_movimientos=suma,
            )
        )
    return salida


@router.get("/variante/{variante_id}", response_model=list[StockOut])
async def stock_de_una_prenda(
    variante_id: uuid.UUID, db: DbSession, _usuario: CurrentUser
) -> list[StockOut]:
    """Dónde está y cuánto hay de una prenda, en todas las sucursales."""
    resultado = await db.execute(
        select(Stock).options(_CON_PRENDA).where(Stock.variante_id == variante_id)
    )
    return [_a_salida(fila) for fila in resultado.scalars().all()]


@router.post("/ingresos", response_model=StockOut, status_code=status.HTTP_201_CREATED)
async def registrar_ingreso(
    datos: IngresoMercaderia, db: DbSession, _encargado: EncargadoUser
) -> StockOut:
    """Suma al stock la mercadería que llegó al local."""
    await _validar_prenda_y_sucursal(db, datos.variante_id, datos.sucursal_id)
    await stock_service.registrar_movimiento(
        db,
        variante_id=datos.variante_id,
        sucursal_id=datos.sucursal_id,
        tipo=TipoMovimiento.ingreso,
        cantidad=datos.cantidad,
        motivo=datos.motivo,
    )
    return await _leer_fila(db, datos.variante_id, datos.sucursal_id)


@router.post("/ajustes", response_model=StockOut, status_code=status.HTTP_201_CREATED)
async def registrar_ajuste(
    datos: AjusteStock, db: DbSession, _encargado: EncargadoUser
) -> StockOut:
    """Deja el stock en la cantidad que se contó, guardando la diferencia.

    Nunca se rechaza por dejar el stock más bajo: el ajuste refleja algo que ya
    pasó en el local. Si se contó menos de lo que el sistema creía, la prenda
    ya no está, y rechazar el ajuste no la trae de vuelta — solo deja el
    sistema mintiendo.
    """
    await _validar_prenda_y_sucursal(db, datos.variante_id, datos.sucursal_id)
    await stock_service.ajustar_a(
        db,
        variante_id=datos.variante_id,
        sucursal_id=datos.sucursal_id,
        cantidad_final=datos.cantidad_final,
        motivo=datos.motivo,
    )
    return await _leer_fila(db, datos.variante_id, datos.sucursal_id)


@router.post("/minimo", response_model=StockOut)
async def definir_minimo(
    datos: MinimoStock, db: DbSession, _encargado: EncargadoUser
) -> StockOut:
    """Define el punto de reposición de una prenda en una sucursal."""
    await _validar_prenda_y_sucursal(db, datos.variante_id, datos.sucursal_id)
    resultado = await db.execute(
        select(Stock).where(
            Stock.variante_id == datos.variante_id,
            Stock.sucursal_id == datos.sucursal_id,
        )
    )
    fila = resultado.scalar_one_or_none()
    if fila is None:
        # Se puede fijar el mínimo de una prenda que todavía no llegó: es la
        # forma de que aparezca en las alertas desde el primer día.
        fila = Stock(
            variante_id=datos.variante_id, sucursal_id=datos.sucursal_id, cantidad=0
        )
        db.add(fila)
    fila.stock_minimo = datos.stock_minimo
    await db.flush()
    return await _leer_fila(db, datos.variante_id, datos.sucursal_id)


async def _leer_fila(
    db: DbSession, variante_id: uuid.UUID, sucursal_id: uuid.UUID
) -> StockOut:
    """Vuelve a leer la fila con la prenda cargada, para responder."""
    resultado = await db.execute(
        select(Stock)
        .options(_CON_PRENDA)
        .where(Stock.variante_id == variante_id, Stock.sucursal_id == sucursal_id)
    )
    return _a_salida(resultado.scalar_one())
