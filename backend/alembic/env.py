"""Configuración de Alembic para migraciones asíncronas."""

import asyncio
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Importar el paquete de modelos completo es lo que hace que `Base.metadata`
# conozca todas las tablas. Un modelo que nadie importó no aparece en el
# autogenerate y su tabla nunca se crea.
import app.models  # noqa: F401  isort:skip

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera el SQL de las migraciones sin conectarse a la base."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Corre las migraciones sobre una conexión ya abierta."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Sin esto, un cambio de largo de un String no se detecta y la
        # migración sale vacía.
        compare_type=True,
        # SQLite no soporta ALTER TABLE para casi nada: el modo "batch" arma
        # la tabla nueva, copia y renombra. En PostgreSQL no cambia nada.
        render_as_batch=settings.database_url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Abre el motor asíncrono y corre las migraciones."""
    configuracion: dict[str, Any] = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        configuracion, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Punto de entrada para el modo con conexión."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
