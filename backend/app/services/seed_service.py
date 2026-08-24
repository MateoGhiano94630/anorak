"""Datos que el sistema da por sentados al arrancar.

Es idempotente: corre en cada arranque y no duplica nada. Sirve para que una
base recién migrada tenga una cuenta con la que entrar.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PASSWORD_SEED_POR_DEFECTO, settings
from app.core.security import hash_password
from app.models.usuario import RolUsuario, Usuario

logger = logging.getLogger(__name__)

# El dominio no puede ser .local ni .test: son nombres de uso reservado y
# `email-validator` (el que usa EmailStr) los rechaza. Con uno de esos, la
# cuenta del seed queda creada pero no puede iniciar sesión nunca.
EMAIL_ADMIN_INICIAL = "admin@anorak.com.ar"


async def seed_inicial(db: AsyncSession) -> None:
    """Crea la cuenta de administrador si falta."""
    resultado = await db.execute(
        select(Usuario).where(Usuario.email == EMAIL_ADMIN_INICIAL)
    )
    if resultado.scalar_one_or_none() is None:
        db.add(
            Usuario(
                nombre="Administrador",
                email=EMAIL_ADMIN_INICIAL,
                password_hash=hash_password(settings.seed_password),
                rol=RolUsuario.admin,
                activo=True,
            )
        )
        logger.info("Cuenta de administrador creada: %s", EMAIL_ADMIN_INICIAL)

    await db.commit()

    if settings.seed_password == PASSWORD_SEED_POR_DEFECTO:
        logger.warning(
            "Las cuentas del seed usan la contraseña de fábrica. "
            "Definí SEED_PASSWORD y cambiala desde el sistema."
        )
