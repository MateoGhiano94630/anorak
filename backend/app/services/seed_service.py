"""Datos que el sistema da por sentados al arrancar.

Es idempotente: corre en cada arranque y no duplica nada. Sirve para que una
base recién migrada tenga una cuenta con la que entrar.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PASSWORD_SEED_POR_DEFECTO, settings
from app.core.security import hash_password
from app.models.caja import MedioPago, TipoMedioPago
from app.models.usuario import RolUsuario, Usuario

logger = logging.getLogger(__name__)

# El dominio no puede ser .local ni .test: son nombres de uso reservado y
# `email-validator` (el que usa EmailStr) los rechaza. Con uno de esos, la
# cuenta del seed queda creada pero no puede iniciar sesión nunca.
EMAIL_ADMIN_INICIAL = "admin@anorak.com.ar"

# Los medios con los que cobra el local. Se cargan al arrancar porque sin al
# menos el efectivo la caja no puede abrirse: la apertura es un movimiento y
# todo movimiento tiene un medio.
#
# La comisión y los días de acreditación quedan en blanco a propósito: los
# pone el dueño con los números de su contrato, y un valor inventado acá
# terminaría en un reporte de rentabilidad como si fuera real.
MEDIOS_INICIALES: list[tuple[str, TipoMedioPago, bool]] = [
    ("Efectivo", TipoMedioPago.efectivo, True),
    ("Débito", TipoMedioPago.tarjeta_debito, False),
    ("Crédito", TipoMedioPago.tarjeta_credito, False),
    ("QR / billetera", TipoMedioPago.qr, False),
    ("Transferencia", TipoMedioPago.transferencia, False),
]


async def seed_inicial(db: AsyncSession) -> None:
    """Crea la cuenta de administrador y los medios de pago si faltan."""
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

    for orden, (nombre, tipo, afecta_efectivo) in enumerate(MEDIOS_INICIALES):
        existente = await db.execute(
            select(MedioPago).where(MedioPago.nombre == nombre)
        )
        if existente.scalar_one_or_none() is None:
            db.add(
                MedioPago(
                    nombre=nombre,
                    tipo=tipo,
                    afecta_efectivo=afecta_efectivo,
                    orden=orden,
                    activo=True,
                )
            )
            logger.info("Medio de pago creado: %s", nombre)

    await db.commit()

    if settings.seed_password == PASSWORD_SEED_POR_DEFECTO:
        logger.warning(
            "Las cuentas del seed usan la contraseña de fábrica. "
            "Definí SEED_PASSWORD y cambiala desde el sistema."
        )
