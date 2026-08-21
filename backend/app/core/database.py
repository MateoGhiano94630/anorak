"""Motor de base de datos, sesión y clase base de los modelos."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

ES_POSTGRES = settings.database_url.startswith("postgresql")

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
)


if ES_POSTGRES:

    @event.listens_for(engine.sync_engine, "connect")
    def _configurar_timeouts(dbapi_connection: Any, _record: Any) -> None:
        """Timeouts del lado del servidor — red de seguridad contra transacciones trabadas.

        Sin esto, una conexión que queda huérfana con la transacción abierta
        (por ejemplo si el navegador del local se cierra a mitad de un cobro)
        retiene los locks de las filas que tocó, y toda operación posterior
        sobre esas filas se cuelga esperando.

        - `lock_timeout`: una escritura que no consigue el lock en 10 s falla
          con error en vez de colgarse. El cajero ve un error, no un spinner.
        - `idle_in_transaction_session_timeout`: PostgreSQL corta las conexiones
          ociosas dentro de una transacción y libera sus locks.

        Va como evento de conexión y no en `connect_args` porque el Session
        Pooler de Supabase descarta los `server_settings` del startup packet,
        mientras que un `SET` explícito sí toma efecto. Corre una vez por
        conexión nueva del pool, no por request.
        """
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET lock_timeout = '10s'")
            cursor.execute("SET idle_in_transaction_session_timeout = '60s'")
        finally:
            cursor.close()


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Clase base de todos los modelos."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI: abre la sesión, commitea al salir bien."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
