"""Cambio y consulta de precios.

Los precios los toca solo el administrador. En un local de ropa el margen es
el negocio: quien atiende puede hacer un descuento en una venta puntual —eso
es otra cosa y tiene su propio tope—, pero cambiar la lista es del dueño.
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.models.precio import Precio
from app.models.producto import Producto, Variante
from app.schemas.precio import CambioPrecio, CambioPrecioMasivo, PrecioOut
from app.services import precio_service

router = APIRouter(tags=["precios"])


@router.post(
    "/variantes/{variante_id}/precio",
    response_model=PrecioOut,
    status_code=status.HTTP_201_CREATED,
)
async def cambiar_precio_variante(
    variante_id: uuid.UUID, datos: CambioPrecio, db: DbSession, _admin: AdminUser
) -> Precio:
    """Pone un precio nuevo a una variante y cierra el anterior."""
    if await db.get(Variante, variante_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    return await precio_service.cambiar_precio(
        db,
        variante_id,
        precio_venta=datos.precio_venta,
        costo=datos.costo,
        precio_mayorista=datos.precio_mayorista,
        motivo=datos.motivo,
    )


@router.post(
    "/productos/{producto_id}/precio",
    response_model=list[PrecioOut],
    status_code=status.HTTP_201_CREATED,
)
async def cambiar_precio_producto(
    producto_id: uuid.UUID,
    datos: CambioPrecioMasivo,
    db: DbSession,
    _admin: AdminUser,
) -> list[Precio]:
    """Pone el mismo precio a todas las variantes activas de un producto.

    Es la forma normal de poner precios en ropa: una remera vale lo mismo en S
    que en L. Si alguna variante tiene que valer distinto, se le cambia
    después de a una.
    """
    producto = await db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")

    activas = [variante for variante in producto.variantes if variante.activa]
    if not activas:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "El producto no tiene ninguna prenda cargada a la que ponerle precio",
        )
    return [
        await precio_service.cambiar_precio(
            db,
            variante.id,
            precio_venta=datos.precio_venta,
            costo=datos.costo,
            precio_mayorista=datos.precio_mayorista,
            motivo=datos.motivo,
        )
        for variante in activas
    ]


@router.get("/variantes/{variante_id}/precios", response_model=list[PrecioOut])
async def historial_de_precios(
    variante_id: uuid.UUID, db: DbSession, _usuario: CurrentUser
) -> list[Precio]:
    """Todos los precios que tuvo una variante, del más nuevo al más viejo."""
    if await db.get(Variante, variante_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    return await precio_service.historial_de(db, variante_id)
