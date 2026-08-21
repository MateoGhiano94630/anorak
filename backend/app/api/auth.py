"""Ingreso al sistema, datos de la sesión y cambio de contraseña propia."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario
from app.schemas.auth import (
    CambioPassword,
    CambioPasswordOk,
    LoginRequest,
    TokenResponse,
    UsuarioActual,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _armar_usuario_actual(db: DbSession, usuario: Usuario) -> UsuarioActual:
    """Completa los datos del usuario con el nombre de su sucursal."""
    sucursal_nombre: str | None = None
    if usuario.sucursal_id is not None:
        resultado = await db.execute(
            select(Sucursal.nombre).where(Sucursal.id == usuario.sucursal_id)
        )
        sucursal_nombre = resultado.scalar_one_or_none()
    return UsuarioActual(
        id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        rol=usuario.rol,
        sucursal_id=usuario.sucursal_id,
        sucursal_nombre=sucursal_nombre,
    )


@router.post("/login", response_model=TokenResponse)
async def login(datos: LoginRequest, db: DbSession) -> TokenResponse:
    """Valida las credenciales y devuelve el token de la sesión."""
    resultado = await db.execute(
        select(Usuario).where(Usuario.email == datos.email.lower())
    )
    usuario = resultado.scalar_one_or_none()

    # Mismo mensaje para email inexistente que para contraseña equivocada: si
    # difieren, el formulario de ingreso pasa a ser una forma de averiguar qué
    # direcciones tienen cuenta.
    if usuario is None or not verify_password(datos.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está dada de baja. Hablá con el administrador.",
        )

    usuario.ultimo_ingreso = datetime.now(UTC)
    db.info["usuario_id"] = usuario.id

    token = create_access_token(
        {"sub": str(usuario.id), "email": usuario.email, "rol": usuario.rol.value}
    )
    return TokenResponse(
        access_token=token, usuario=await _armar_usuario_actual(db, usuario)
    )


@router.get("/me", response_model=UsuarioActual)
async def leer_usuario_actual(usuario: CurrentUser, db: DbSession) -> UsuarioActual:
    """Devuelve quién está usando el sistema en esta sesión."""
    return await _armar_usuario_actual(db, usuario)


@router.post("/cambiar-password", response_model=CambioPasswordOk)
async def cambiar_password(
    datos: CambioPassword, usuario: CurrentUser, _db: DbSession
) -> CambioPasswordOk:
    """Cambia la contraseña propia, verificando la anterior."""
    if not verify_password(datos.password_actual, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta",
        )
    usuario.password_hash = hash_password(datos.password_nueva)
    return CambioPasswordOk()
