"""Mide, desde adentro del servidor, a dónde se va el tiempo de un pedido.

Existe porque desde afuera el dato no se puede obtener. Un `curl` mide el
viaje entero —navegador, red, servidor, base— y devuelve un solo número: no
sabe qué parte fue de cada cosa, así que un backend lento y una base lejana se
ven exactamente igual. Las dos preguntas que importan cuando el ingreso tarda
son "¿cuánto tarda Railway en hablarle a Supabase?" y "¿cuánto tarda esta
máquina en calcular un bcrypt?", y las dos solo se pueden contestar corriendo
la medición donde está el servidor.

Es una herramienta de diagnóstico, no una parte del sistema. Cuando el
problema esté resuelto, se puede borrar el módulo y su endpoint sin que nada
más se entere.
"""

import statistics
import time
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core import database
from app.core.config import settings
from app.core.database import CONNECT_ARGS, ES_POSTGRES, configurar_conexion
from app.core.security import hashear_password

# La primera medición se descarta y se toma la mediana de las que siguen: la
# primera consulta de una conexión recién abierta arrastra el costo de abrirla,
# y un pico suelto de la red no tiene que ensuciar el número.
MUESTRAS_IDA_Y_VUELTA = 5


def _ms(desde: float) -> float:
    """Milisegundos transcurridos, redondeados a una décima."""
    return round((time.perf_counter() - desde) * 1000, 1)


async def _medir_conexion_nueva() -> float:
    """Cuánto cuesta abrir una conexión desde cero: TCP, TLS y saludo del pooler.

    Va con `NullPool` y un motor descartable para que la medición sea de una
    conexión de verdad nueva. Usando el motor de la aplicación devolvería el
    costo de sacar una del pool, que es cero y no dice nada.
    """
    motor = create_async_engine(
        settings.database_url, poolclass=NullPool, connect_args=CONNECT_ARGS
    )
    if ES_POSTGRES:
        event.listen(motor.sync_engine, "connect", configurar_conexion)
    try:
        inicio = time.perf_counter()
        async with motor.connect():
            return _ms(inicio)
    finally:
        await motor.dispose()


async def _medir_ida_y_vuelta() -> float:
    """El viaje de ida y vuelta a la base, sobre una conexión ya abierta.

    Este es el número que dice si la región importa. Es la latencia pura entre
    el servidor y la base: un `SELECT 1` no le da trabajo a PostgreSQL, así que
    lo que se mide es el camino.

    El motor se busca por atributo del módulo, y no importado por nombre, para
    que los tests puedan apuntarlo a la base en memoria — la misma razón por la
    que `conftest.py` sustituye `database.AsyncSessionLocal`.
    """
    async with database.engine.connect() as conexion:
        await conexion.execute(text("SELECT 1"))
        muestras: list[float] = []
        for _ in range(MUESTRAS_IDA_Y_VUELTA):
            inicio = time.perf_counter()
            await conexion.execute(text("SELECT 1"))
            muestras.append(_ms(inicio))
    return statistics.median(muestras)


async def _medir_bcrypt() -> float:
    """Cuánto tarda un bcrypt en esta máquina.

    Multiplicado por la cantidad de viajes a la base, es casi todo el tiempo de
    un ingreso. Sirve para saber si el contenedor de Railway tiene CPU o le
    tocó un vecino ruidoso.
    """
    inicio = time.perf_counter()
    await hashear_password("medicion-de-diagnostico")
    return _ms(inicio)


async def medir_tiempos() -> dict[str, Any]:
    """Corre las tres mediciones y devuelve los números, sin fallar nunca.

    Cada medición va con su propio `try`: si la base no responde, el resto de
    los datos igual sirve, y saber *cuál* falló ya es media respuesta.

    No devuelve nada secreto. El host de la base sale sin usuario ni
    contraseña, y es justamente el dato que hace falta: la región de Supabase
    está escrita en el nombre (`aws-0-us-east-1.pooler.supabase.com`).
    """
    partes = urlparse(settings.database_url)
    resultado: dict[str, Any] = {
        "entorno": settings.environment,
        "base": {
            "host": partes.hostname,
            "motor": "postgresql" if ES_POSTGRES else "sqlite",
            "eco_sql": settings.environment == "development",
        },
    }

    try:
        resultado["base"]["conexion_nueva_ms"] = await _medir_conexion_nueva()
    except Exception as error:
        resultado["base"]["conexion_nueva_ms"] = None
        resultado["base"]["error"] = f"{type(error).__name__}: {error}"

    try:
        resultado["base"]["ida_y_vuelta_ms"] = await _medir_ida_y_vuelta()
    except Exception as error:
        resultado["base"]["ida_y_vuelta_ms"] = None
        resultado["base"].setdefault("error", f"{type(error).__name__}: {error}")

    resultado["cpu"] = {"bcrypt_ms": await _medir_bcrypt()}

    ida_y_vuelta = resultado["base"]["ida_y_vuelta_ms"]
    if ida_y_vuelta is not None:
        # Un ingreso son cinco viajes a la base más un bcrypt. Es una cuenta,
        # no una medición: sirve para comparar contra lo que tarda de verdad y
        # ver si falta tiempo por explicar.
        resultado["ingreso_estimado_ms"] = round(
            ida_y_vuelta * 5 + resultado["cpu"]["bcrypt_ms"], 1
        )

    return resultado
