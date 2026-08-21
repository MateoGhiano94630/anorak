"""Alta y mantenimiento de sucursales."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.models.sucursal import Sucursal
from app.schemas.sucursal import SucursalCreate, SucursalOut, SucursalUpdate

router = APIRouter(prefix="/sucursales", tags=["sucursales"])


@router.get("", response_model=list[SucursalOut])
async def listar_sucursales(db: DbSession, _usuario: CurrentUser) -> list[Sucursal]:
    """Lista las sucursales. La lee cualquier usuario: el selector de sucursal
    aparece en pantallas de stock y de caja."""
    resultado = await db.execute(select(Sucursal).order_by(Sucursal.nombre))
    return list(resultado.scalars().all())


@router.post("", response_model=SucursalOut, status_code=status.HTTP_201_CREATED)
async def crear_sucursal(
    datos: SucursalCreate, db: DbSession, _admin: AdminUser
) -> Sucursal:
    """Da de alta una sucursal o un depósito."""
    codigo = datos.codigo.upper()
    existente = await db.execute(select(Sucursal).where(Sucursal.codigo == codigo))
    if existente.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una sucursal con ese código",
        )
    sucursal = Sucursal(**{**datos.model_dump(), "codigo": codigo})
    db.add(sucursal)
    await db.flush()
    return sucursal


@router.patch("/{sucursal_id}", response_model=SucursalOut)
async def modificar_sucursal(
    sucursal_id: uuid.UUID, datos: SucursalUpdate, db: DbSession, _admin: AdminUser
) -> Sucursal:
    """Modifica una sucursal. El código no se cambia: identifica movimientos
    ya registrados."""
    sucursal = await db.get(Sucursal, sucursal_id)
    if sucursal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada"
        )
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(sucursal, campo, valor)
    await db.flush()
    return sucursal
