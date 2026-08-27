"""Motor de base de datos, sesión y clase base de los modelos."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

ES_POSTGRES = settings.database_url.startswith("postgresql")

# ── Techos de tiempo ─────────────────────────────────────────────────────────
#
# Los tres existen por la misma razón: sin ellos, una base que dejó de
# contestar deja el pedido colgado para siempre, y quien está en el mostrador
# ve un spinner que no termina nunca y no dice nada. Un error a los quince
# segundos es peor que una respuesta, pero es muchísimo mejor que un sistema
# que parece trabado: se puede reintentar, y se sabe qué pasó.
#
# Ninguna consulta de este sistema se acerca al techo: las tablas son chicas y
# lo más grande que se lee son los movimientos de una jornada.
#
# Las migraciones **no** quedan alcanzadas por esto: `alembic/env.py` arma su
# propio motor con `async_engine_from_config`, así que un `alembic upgrade` que
# tarde en una tabla grande no se corta a los quince segundos.
TIMEOUT_CONSULTA_SEGUNDOS = 15

# El de la biblioteca cliente va por encima del del servidor a propósito: si
# PostgreSQL sigue vivo, corta él y el error dice qué consulta fue. Este es la
# red de abajo, para cuando la conexión se cortó y del otro lado no hay nadie
# que pueda cortar nada.
TIMEOUT_COMANDO_SEGUNDOS = 20

# Abrir una conexión es TCP, TLS y el saludo del pooler. Si en diez segundos no
# se pudo, no se va a poder: la base está pausada o inalcanzable, y esperar
# sesenta —el valor de fábrica de asyncpg— solo alarga la agonía.
TIMEOUT_CONEXION_SEGUNDOS = 10

# Cuánto espera un pedido a que se libere una conexión del pool. De fábrica son
# treinta segundos, que para un mostrador es lo mismo que colgarse.
TIMEOUT_POOL_SEGUNDOS = 10


def configurar_conexion(dbapi_connection: Any, _record: Any = None) -> None:
    """Timeouts del lado del servidor — red de seguridad contra transacciones trabadas.

    Sin esto, una conexión que queda huérfana con la transacción abierta
    (por ejemplo si el navegador del local se cierra a mitad de un cobro)
    retiene los locks de las filas que tocó, y toda operación posterior
    sobre esas filas se cuelga esperando.

    - `statement_timeout`: una consulta que se pasa del techo falla con error.
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
        cursor.execute(f"SET statement_timeout = '{TIMEOUT_CONSULTA_SEGUNDOS}s'")
        cursor.execute("SET lock_timeout = '10s'")
        cursor.execute("SET idle_in_transaction_session_timeout = '60s'")
    finally:
        cursor.close()


# asyncpg acepta estos dos; el driver de SQLite no conoce ninguno, así que el
# diccionario queda vacío cuando los tests corren en memoria.
CONNECT_ARGS: dict[str, Any] = (
    {
        "timeout": TIMEOUT_CONEXION_SEGUNDOS,
        "command_timeout": TIMEOUT_COMANDO_SEGUNDOS,
    }
    if ES_POSTGRES
    else {}
)

# `pool_timeout` es de QueuePool. El motor de SQLite usa NullPool, que no lo
# acepta y hace fallar la creación del motor entera.
_OPCIONES_POOL: dict[str, Any] = (
    {"pool_timeout": TIMEOUT_POOL_SEGUNDOS} if ES_POSTGRES else {}
)

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
    connect_args=CONNECT_ARGS,
    **_OPCIONES_POOL,
)


if ES_POSTGRES:
    event.listen(engine.sync_engine, "connect", configurar_conexion)


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
