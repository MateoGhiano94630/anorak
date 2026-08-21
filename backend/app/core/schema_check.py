"""Chequeo de que la base esté al día con las migraciones del código."""

import logging
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.core.database import engine

logger = logging.getLogger(__name__)


async def verificar_esquema_al_dia() -> None:
    """Compara la revisión de la base contra la última del código.

    Loguea fuerte pero no frena el arranque: si el backend no levanta, el
    local no vende. Un aviso ruidoso en los logs alcanza para enterarse, y
    dejar la API caída por una migración pendiente es peor que el problema.
    """
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        head = ScriptDirectory.from_config(config).get_current_head()
        async with engine.connect() as conexion:
            resultado = await conexion.execute(
                text("SELECT version_num FROM alembic_version")
            )
            actual = resultado.scalar_one_or_none()
    except Exception:
        logger.warning("No se pudo verificar el esquema de la base")
        return

    if actual != head:
        logger.error(
            "La base está en la revisión %s y el código espera %s. "
            "Falta correr `alembic upgrade head`.",
            actual,
            head,
        )
