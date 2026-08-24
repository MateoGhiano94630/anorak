"""Administración de usuarios. Solo para el rol admin."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import AdminUser, DbSession
from app.core.security import hash_password
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(db: DbSession, _admin: AdminUser) -> list[Usuario]:
    """Lista todas las cuentas, activas y dadas de baja."""
    resultado = await db.execute(select(Usuario).order_by(Usuario.nombre))
    return list(resultado.scalars().all())


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    datos: UsuarioCreate, db: DbSession, _admin: AdminUser
) -> Usuario:
    """Da de alta una cuenta."""
    email = datos.email.lower()
    existente = await db.execute(select(Usuario).where(Usuario.email == email))
    if existente.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email",
        )
    usuario = Usuario(
        nombre=datos.nombre,
        email=email,
        password_hash=hash_password(datos.password),
        rol=datos.rol,
        activo=True,
    )
    db.add(usuario)
    await db.flush()
    return usuario


@router.get("/{usuario_id}", response_model=UsuarioOut)
async def leer_usuario(
    usuario_id: uuid.UUID, db: DbSession, _admin: AdminUser
) -> Usuario:
    """Devuelve una cuenta por su identificador."""
    usuario = await db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )
    return usuario


@router.patch("/{usuario_id}", response_model=UsuarioOut)
async def modificar_usuario(
    usuario_id: uuid.UUID, datos: UsuarioUpdate, db: DbSession, admin: AdminUser
) -> Usuario:
    """Modifica una cuenta. Dar de baja es `activo = false`, nunca borrar:
    los usuarios son el "quién" de cada movimiento histórico."""
    usuario = await db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )
    cambios = datos.model_dump(exclude_unset=True)
    if "email" in cambios and cambios["email"] is not None:
        cambios["email"] = cambios["email"].lower()
        duplicado = await db.execute(
            select(Usuario).where(
                Usuario.email == cambios["email"], Usuario.id != usuario_id
            )
        )
        if duplicado.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una cuenta con ese email",
            )
    # Un admin que se da de baja a sí mismo deja el sistema sin quien
    # administre. Pasó una vez y hubo que arreglarlo por consola.
    if cambios.get("activo") is False and usuario.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No podés dar de baja tu propia cuenta",
        )
    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)
    await db.flush()
    return usuario
