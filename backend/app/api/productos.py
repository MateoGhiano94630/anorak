"""Productos, variantes e imágenes."""

import logging
import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession, EncargadoUser
from app.models.catalogo import Categoria, Marca
from app.models.precio import Precio
from app.models.producto import ImagenProducto, Producto, Variante
from app.schemas.producto import (
    GenerarVariantes,
    ImagenOut,
    ProductoCreate,
    ProductoEnLista,
    ProductoOut,
    ProductoUpdate,
    VarianteOut,
    VarianteUpdate,
)
from app.services import catalogo_service, r2_service
from app.services.precio_service import precio_vigente, precios_vigentes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/productos", tags=["catálogo"])
variantes_router = APIRouter(prefix="/variantes", tags=["catálogo"])


def _url_de(imagen: ImagenProducto) -> str | None:
    """Dirección temporal de una foto, o None si no se puede armar.

    Que falte una foto no puede tumbar la pantalla de catálogo: si R2 no está
    configurado en este servidor, o no contesta, el producto se muestra igual
    sin la imagen.
    """
    if not r2_service.esta_configurado():
        return None
    try:
        return r2_service.url_firmada(imagen.clave)
    except Exception:
        logger.exception("No se pudo firmar la dirección de la imagen %s", imagen.clave)
        return None


def _variante_a_salida(variante: Variante, precio: Precio | None) -> VarianteOut:
    """Arma la variante con su talle, color y precio vigente."""
    return VarianteOut(
        id=variante.id,
        producto_id=variante.producto_id,
        talle_id=variante.talle_id,
        talle=variante.talle.valor,
        color_id=variante.color_id,
        color=variante.color.nombre,
        codigo_hex=variante.color.codigo_hex,
        sku=variante.sku,
        codigo_barras=variante.codigo_barras,
        activa=variante.activa,
        precio_venta=precio.precio_venta if precio is not None else None,
        costo=precio.costo if precio is not None else None,
    )


async def _producto_a_salida(db: DbSession, producto: Producto) -> ProductoOut:
    """Arma el producto completo: variantes con precio e imágenes con dirección."""
    precios = await precios_vigentes(db, [v.id for v in producto.variantes])
    variantes = sorted(
        producto.variantes, key=lambda v: (v.talle.orden, v.color.nombre)
    )
    return ProductoOut(
        id=producto.id,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        categoria_id=producto.categoria_id,
        categoria=producto.categoria.nombre,
        marca_id=producto.marca_id,
        marca=producto.marca.nombre if producto.marca is not None else None,
        genero=producto.genero,
        temporada=producto.temporada,
        activo=producto.activo,
        variantes=[
            _variante_a_salida(variante, precios.get(variante.id))
            for variante in variantes
        ],
        imagenes=[
            ImagenOut(id=imagen.id, orden=imagen.orden, url=_url_de(imagen))
            for imagen in producto.imagenes
        ],
    )


async def _traer_producto(db: DbSession, producto_id: uuid.UUID) -> Producto:
    """Trae el producto o corta con 404."""
    producto = await db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return producto


@router.get("", response_model=list[ProductoEnLista])
async def listar_productos(
    db: DbSession,
    _usuario: CurrentUser,
    buscar: str | None = None,
    categoria_id: uuid.UUID | None = None,
    marca_id: uuid.UUID | None = None,
    solo_activos: bool = True,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ProductoEnLista]:
    """Lista el catálogo con el rango de precios y la foto principal.

    Devuelve el rango y no el precio de cada variante: en el listado lo que se
    quiere ver es cuánto vale la prenda, y el detalle por talle está a un
    toque de distancia.
    """
    consulta = select(Producto).order_by(Producto.nombre).limit(limite)
    if solo_activos:
        consulta = consulta.where(Producto.activo.is_(True))
    if categoria_id is not None:
        consulta = consulta.where(Producto.categoria_id == categoria_id)
    if marca_id is not None:
        consulta = consulta.where(Producto.marca_id == marca_id)
    if buscar:
        patron = f"%{buscar.strip()}%"
        consulta = consulta.where(
            or_(Producto.nombre.ilike(patron), Producto.descripcion.ilike(patron))
        )

    productos = list((await db.execute(consulta)).scalars().all())
    if not productos:
        return []

    # Los precios de todas las variantes de la página, en una sola consulta.
    # Pedirlos de a un producto convierte el catálogo en cincuenta consultas.
    variante_ids = [v.id for p in productos for v in p.variantes]
    rangos: dict[uuid.UUID, tuple[Decimal | None, Decimal | None]] = {}
    if variante_ids:
        filas = await db.execute(
            select(
                Variante.producto_id,
                func.min(Precio.precio_venta),
                func.max(Precio.precio_venta),
            )
            .join(Precio, Precio.variante_id == Variante.id)
            .where(Variante.id.in_(variante_ids), Precio.vigente_hasta.is_(None))
            .group_by(Variante.producto_id)
        )
        rangos = {fila[0]: (fila[1], fila[2]) for fila in filas.all()}

    salida: list[ProductoEnLista] = []
    for producto in productos:
        desde, hasta = rangos.get(producto.id, (None, None))
        salida.append(
            ProductoEnLista(
                id=producto.id,
                nombre=producto.nombre,
                categoria=producto.categoria.nombre,
                marca=producto.marca.nombre if producto.marca is not None else None,
                genero=producto.genero,
                temporada=producto.temporada,
                activo=producto.activo,
                cantidad_variantes=len(producto.variantes),
                precio_desde=desde,
                precio_hasta=hasta,
                imagen_url=_url_de(producto.imagenes[0]) if producto.imagenes else None,
            )
        )
    return salida


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
async def crear_producto(
    datos: ProductoCreate, db: DbSession, _encargado: EncargadoUser
) -> ProductoOut:
    """Da de alta un producto, todavía sin variantes."""
    if await db.get(Categoria, datos.categoria_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La categoría no existe")
    if datos.marca_id is not None and await db.get(Marca, datos.marca_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La marca no existe")

    producto = Producto(**datos.model_dump(), activo=True)
    db.add(producto)
    await db.flush()
    await db.refresh(producto)
    return await _producto_a_salida(db, producto)


@router.get("/{producto_id}", response_model=ProductoOut)
async def leer_producto(
    producto_id: uuid.UUID, db: DbSession, _usuario: CurrentUser
) -> ProductoOut:
    """Devuelve un producto con todas sus variantes y sus precios."""
    return await _producto_a_salida(db, await _traer_producto(db, producto_id))


@router.patch("/{producto_id}", response_model=ProductoOut)
async def modificar_producto(
    producto_id: uuid.UUID,
    datos: ProductoUpdate,
    db: DbSession,
    _encargado: EncargadoUser,
) -> ProductoOut:
    """Modifica un producto.

    Cambiar la categoría no borra las variantes que ya existen, aunque sus
    talles no estén en la curva de la categoría nueva: esas variantes ya
    tienen stock y movimientos, y borrarlas sería perder historia. Lo que sí
    hace el sistema es negarse a generar variantes nuevas con talles que no
    correspondan.
    """
    producto = await _traer_producto(db, producto_id)
    cambios = datos.model_dump(exclude_unset=True)
    if (
        cambios.get("categoria_id") is not None
        and await db.get(Categoria, cambios["categoria_id"]) is None
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La categoría no existe")
    if (
        cambios.get("marca_id") is not None
        and await db.get(Marca, cambios["marca_id"]) is None
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La marca no existe")
    for campo, valor in cambios.items():
        setattr(producto, campo, valor)
    await db.flush()
    await db.refresh(producto)
    return await _producto_a_salida(db, producto)


@router.post(
    "/{producto_id}/variantes",
    response_model=ProductoOut,
    status_code=status.HTTP_201_CREATED,
)
async def generar_variantes(
    producto_id: uuid.UUID,
    datos: GenerarVariantes,
    db: DbSession,
    _encargado: EncargadoUser,
) -> ProductoOut:
    """Genera todas las combinaciones de talle y color elegidas.

    Las que ya existían se saltean, así sumar un color a un producto cargado
    es volver a ejecutar esto con el color nuevo.
    """
    producto = await _traer_producto(db, producto_id)
    try:
        await catalogo_service.generar_variantes(
            db, producto, datos.talle_ids, datos.color_ids
        )
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err
    await db.refresh(producto)
    return await _producto_a_salida(db, producto)


@router.post(
    "/{producto_id}/imagenes",
    response_model=ImagenOut,
    status_code=status.HTTP_201_CREATED,
)
async def subir_imagen(
    producto_id: uuid.UUID,
    db: DbSession,
    _encargado: EncargadoUser,
    archivo: Annotated[UploadFile, File()],
) -> ImagenOut:
    """Sube una foto del producto."""
    producto = await _traer_producto(db, producto_id)

    extension = r2_service.FORMATOS_ACEPTADOS.get(archivo.content_type or "")
    if extension is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La foto tiene que ser JPG, PNG o WEBP.",
        )
    contenido = await archivo.read()
    if len(contenido) > r2_service.TAMANIO_MAXIMO_BYTES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La foto pesa más de 3 MB. Sacale una más chica o recortala.",
        )

    clave = r2_service.clave_para(producto_id, extension)
    try:
        r2_service.subir_imagen(clave, contenido, archivo.content_type or "image/jpeg")
    except r2_service.R2NoConfiguradoError as err:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(err)) from err

    imagen = ImagenProducto(
        producto_id=producto_id,
        clave=clave,
        nombre_original=archivo.filename,
        orden=len(producto.imagenes),
    )
    db.add(imagen)
    await db.flush()
    return ImagenOut(id=imagen.id, orden=imagen.orden, url=_url_de(imagen))


@router.delete("/imagenes/{imagen_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_imagen(
    imagen_id: uuid.UUID, db: DbSession, _encargado: EncargadoUser
) -> None:
    """Borra una foto del producto y del guardado de imágenes."""
    imagen = await db.get(ImagenProducto, imagen_id)
    if imagen is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Imagen no encontrada")
    r2_service.eliminar_imagen(imagen.clave)
    await db.delete(imagen)
    await db.flush()


# ── Variantes ─────────────────────────────────────────────────────────────────


@variantes_router.get("/buscar", response_model=VarianteOut)
async def buscar_variante(
    codigo: str, db: DbSession, _usuario: CurrentUser
) -> VarianteOut:
    """Busca una variante por su código interno o el de barras.

    Es lo que va a usar el lector del mostrador: pasa la etiqueta y aparece la
    prenda. Busca por los dos códigos porque no toda la ropa viene con código
    de barras del proveedor.
    """
    limpio = codigo.strip()
    resultado = await db.execute(
        select(Variante).where(
            or_(Variante.sku == limpio, Variante.codigo_barras == limpio)
        )
    )
    variante = resultado.scalar_one_or_none()
    if variante is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No hay ninguna prenda con ese código"
        )
    return _variante_a_salida(variante, await precio_vigente(db, variante.id))


@variantes_router.patch("/{variante_id}", response_model=VarianteOut)
async def modificar_variante(
    variante_id: uuid.UUID,
    datos: VarianteUpdate,
    db: DbSession,
    _encargado: EncargadoUser,
) -> VarianteOut:
    """Corrige el código interno o el de barras de una variante."""
    variante = await db.get(Variante, variante_id)
    if variante is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(variante, campo, valor.strip() if isinstance(valor, str) else valor)
    try:
        await db.flush()
    except IntegrityError as err:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ese código ya lo tiene otra prenda"
        ) from err
    return _variante_a_salida(variante, await precio_vigente(db, variante_id))
