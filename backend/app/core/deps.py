"""Dependencias compartidas por los endpoints: sesión, usuario actual, roles."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.usuario import RolUsuario, Usuario

# El token viaja siempre en el header Authorization. No hay cookie ni
# localStorage: el frontend lo guarda en memoria (ver docs/arquitectura.md).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> Usuario:
    """Valida el JWT y devuelve el usuario activo que lo firmó."""
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        usuario_id = payload.get("sub")
    except JWTError as err:
        raise credenciales_invalidas from err
    if usuario_id is None:
        raise credenciales_invalidas

    resultado = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = resultado.scalar_one_or_none()
    if usuario is None or not usuario.activo:
        raise credenciales_invalidas

    # Datos para el listener de auditoría (app/core/audit.py). La Session no
    # tiene forma de saber quién está escribiendo ni desde dónde, así que se
    # los dejamos acá para que el `before_flush` los lea en cada flush.
    db.info["usuario_id"] = usuario.id
    db.info["ip_origen"] = request.client.host if request.client else None

    return usuario


def requiere_rol(*roles: RolUsuario) -> object:
    """Arma una dependencia que solo deja pasar a los roles indicados.

    El admin entra siempre: es superset de todos los permisos del sistema, y
    repetirlo en cada llamada era la forma de olvidárselo en alguna.
    """

    async def verificar(
        usuario: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if usuario.rol == RolUsuario.admin or usuario.rol in roles:
            return usuario
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permiso para esta operación",
        )

    return Depends(verificar)


# Tipos anotados para usar directamente en la firma de los endpoints.
CurrentUser = Annotated[Usuario, Depends(get_current_user)]
AdminUser = Annotated[Usuario, requiere_rol()]
EncargadoUser = Annotated[Usuario, requiere_rol(RolUsuario.encargado)]
