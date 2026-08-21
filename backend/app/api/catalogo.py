"""Marcas, curvas de talle, colores y categorías.

Los lee cualquier usuario —el mostrador necesita saber qué talles y colores
existen— y los edita el encargado o el administrador.
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession, EncargadoUser
from app.models.catalogo import Categoria, Color, CurvaTalle, Marca, Talle
from app.schemas.catalogo import (
    CategoriaCreate,
    CategoriaOut,
    CategoriaUpdate,
    ColorCreate,
    ColorOut,
    ColorUpdate,
    CurvaTalleCreate,
    CurvaTalleOut,
    CurvaTalleUpdate,
    MarcaCreate,
    MarcaOut,
    MarcaUpdate,
    TalleCreate,
    TalleOut,
)

marcas_router = APIRouter(prefix="/marcas", tags=["catálogo"])
curvas_router = APIRouter(prefix="/curvas-talle", tags=["catálogo"])
colores_router = APIRouter(prefix="/colores", tags=["catálogo"])
categorias_router = APIRouter(prefix="/categorias", tags=["catálogo"])


def _ya_existe(nombre_entidad: str) -> HTTPException:
    """El error de nombre repetido, con el mismo texto en todos los catálogos."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Ya existe {nombre_entidad} con ese nombre",
    )


# ── Marcas ────────────────────────────────────────────────────────────────────


@marcas_router.get("", response_model=list[MarcaOut])
async def listar_marcas(db: DbSession, _usuario: CurrentUser) -> list[Marca]:
    """Lista las marcas, alfabéticamente."""
    resultado = await db.execute(select(Marca).order_by(Marca.nombre))
    return list(resultado.scalars().all())


@marcas_router.post("", response_model=MarcaOut, status_code=status.HTTP_201_CREATED)
async def crear_marca(
    datos: MarcaCreate, db: DbSession, _encargado: EncargadoUser
) -> Marca:
    """Da de alta una marca."""
    nombre = datos.nombre.strip()
    existente = await db.execute(select(Marca).where(Marca.nombre == nombre))
    if existente.scalar_one_or_none() is not None:
        raise _ya_existe("una marca")
    marca = Marca(nombre=nombre, activa=True)
    db.add(marca)
    await db.flush()
    return marca


@marcas_router.patch("/{marca_id}", response_model=MarcaOut)
async def modificar_marca(
    marca_id: uuid.UUID, datos: MarcaUpdate, db: DbSession, _encargado: EncargadoUser
) -> Marca:
    """Modifica una marca."""
    marca = await db.get(Marca, marca_id)
    if marca is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Marca no encontrada")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(marca, campo, valor.strip() if campo == "nombre" else valor)
    try:
        await db.flush()
    except IntegrityError as err:
        raise _ya_existe("una marca") from err
    return marca


# ── Curvas de talle ───────────────────────────────────────────────────────────


@curvas_router.get("", response_model=list[CurvaTalleOut])
async def listar_curvas(db: DbSession, _usuario: CurrentUser) -> list[CurvaTalle]:
    """Lista las curvas con sus talles."""
    resultado = await db.execute(select(CurvaTalle).order_by(CurvaTalle.nombre))
    return list(resultado.scalars().all())


@curvas_router.post(
    "", response_model=CurvaTalleOut, status_code=status.HTTP_201_CREATED
)
async def crear_curva(
    datos: CurvaTalleCreate, db: DbSession, _encargado: EncargadoUser
) -> CurvaTalle:
    """Da de alta una curva con todos sus talles."""
    nombre = datos.nombre.strip()
    existente = await db.execute(select(CurvaTalle).where(CurvaTalle.nombre == nombre))
    if existente.scalar_one_or_none() is not None:
        raise _ya_existe("una curva")

    valores = [talle.valor.strip() for talle in datos.talles]
    if len(set(valores)) != len(valores):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "La curva tiene talles repetidos"
        )

    curva = CurvaTalle(nombre=nombre, activa=True)
    db.add(curva)
    await db.flush()
    for orden, talle in enumerate(datos.talles):
        db.add(
            Talle(
                curva_talle_id=curva.id,
                valor=talle.valor.strip(),
                # Si no se indica el orden, vale la posición en la que se
                # cargaron: alfabéticamente L va antes que M, que es al revés
                # de como los busca cualquiera.
                orden=talle.orden if talle.orden != 0 else orden,
                activo=True,
            )
        )
    await db.flush()
    await db.refresh(curva)
    return curva


@curvas_router.patch("/{curva_id}", response_model=CurvaTalleOut)
async def modificar_curva(
    curva_id: uuid.UUID,
    datos: CurvaTalleUpdate,
    db: DbSession,
    _encargado: EncargadoUser,
) -> CurvaTalle:
    """Modifica el nombre o el estado de una curva."""
    curva = await db.get(CurvaTalle, curva_id)
    if curva is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Curva no encontrada")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(curva, campo, valor.strip() if campo == "nombre" else valor)
    await db.flush()
    return curva


@curvas_router.post(
    "/{curva_id}/talles", response_model=TalleOut, status_code=status.HTTP_201_CREATED
)
async def agregar_talle(
    curva_id: uuid.UUID, datos: TalleCreate, db: DbSession, _encargado: EncargadoUser
) -> Talle:
    """Suma un talle a una curva que ya existe."""
    curva = await db.get(CurvaTalle, curva_id)
    if curva is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Curva no encontrada")
    valor = datos.valor.strip()
    if any(talle.valor == valor for talle in curva.talles):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esa curva ya tiene un talle con ese nombre"
        )
    talle = Talle(
        curva_talle_id=curva_id,
        valor=valor,
        orden=datos.orden if datos.orden != 0 else len(curva.talles),
        activo=True,
    )
    db.add(talle)
    await db.flush()
    return talle


# ── Colores ───────────────────────────────────────────────────────────────────


@colores_router.get("", response_model=list[ColorOut])
async def listar_colores(db: DbSession, _usuario: CurrentUser) -> list[Color]:
    """Lista los colores, alfabéticamente."""
    resultado = await db.execute(select(Color).order_by(Color.nombre))
    return list(resultado.scalars().all())


@colores_router.post("", response_model=ColorOut, status_code=status.HTTP_201_CREATED)
async def crear_color(
    datos: ColorCreate, db: DbSession, _encargado: EncargadoUser
) -> Color:
    """Da de alta un color."""
    nombre = datos.nombre.strip()
    existente = await db.execute(select(Color).where(Color.nombre == nombre))
    if existente.scalar_one_or_none() is not None:
        raise _ya_existe("un color")
    color = Color(nombre=nombre, codigo_hex=datos.codigo_hex, activo=True)
    db.add(color)
    await db.flush()
    return color


@colores_router.patch("/{color_id}", response_model=ColorOut)
async def modificar_color(
    color_id: uuid.UUID, datos: ColorUpdate, db: DbSession, _encargado: EncargadoUser
) -> Color:
    """Modifica un color."""
    color = await db.get(Color, color_id)
    if color is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Color no encontrado")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(color, campo, valor.strip() if campo == "nombre" else valor)
    try:
        await db.flush()
    except IntegrityError as err:
        raise _ya_existe("un color") from err
    return color


# ── Categorías ────────────────────────────────────────────────────────────────


def _a_salida(categoria: Categoria) -> CategoriaOut:
    """Arma la categoría con el nombre de su curva, para no pedirlo aparte."""
    return CategoriaOut(
        id=categoria.id,
        nombre=categoria.nombre,
        curva_talle_id=categoria.curva_talle_id,
        curva_nombre=categoria.curva.nombre,
        activa=categoria.activa,
    )


@categorias_router.get("", response_model=list[CategoriaOut])
async def listar_categorias(db: DbSession, _usuario: CurrentUser) -> list[CategoriaOut]:
    """Lista las categorías con la curva de talles que usa cada una."""
    resultado = await db.execute(select(Categoria).order_by(Categoria.nombre))
    return [_a_salida(categoria) for categoria in resultado.scalars().all()]


@categorias_router.post(
    "", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED
)
async def crear_categoria(
    datos: CategoriaCreate, db: DbSession, _encargado: EncargadoUser
) -> CategoriaOut:
    """Da de alta una categoría."""
    nombre = datos.nombre.strip()
    existente = await db.execute(select(Categoria).where(Categoria.nombre == nombre))
    if existente.scalar_one_or_none() is not None:
        raise _ya_existe("una categoría")
    if await db.get(CurvaTalle, datos.curva_talle_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La curva de talles no existe")

    categoria = Categoria(
        nombre=nombre, curva_talle_id=datos.curva_talle_id, activa=True
    )
    db.add(categoria)
    await db.flush()
    await db.refresh(categoria)
    return _a_salida(categoria)


@categorias_router.patch("/{categoria_id}", response_model=CategoriaOut)
async def modificar_categoria(
    categoria_id: uuid.UUID,
    datos: CategoriaUpdate,
    db: DbSession,
    _encargado: EncargadoUser,
) -> CategoriaOut:
    """Modifica una categoría."""
    categoria = await db.get(Categoria, categoria_id)
    if categoria is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    cambios = datos.model_dump(exclude_unset=True)
    if (
        cambios.get("curva_talle_id") is not None
        and await db.get(CurvaTalle, cambios["curva_talle_id"]) is None
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La curva de talles no existe")
    for campo, valor in cambios.items():
        setattr(categoria, campo, valor.strip() if campo == "nombre" else valor)
    await db.flush()
    await db.refresh(categoria)
    return _a_salida(categoria)
