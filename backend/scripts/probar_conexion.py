"""
Prueba una URL de base de datos sin desplegar nada.

Un despliegue en Railway tarda minutos y solo dice "password authentication
failed". Esto tarda dos segundos y dice **qué** está mal.

    .venv/bin/python scripts/probar_conexion.py "postgresql+asyncpg://..."

Si no se le pasa la URL, usa la que esté configurada (`DATABASE_URL` del
entorno o de `backend/.env`). Nunca imprime la contraseña.
"""

import asyncio
import sys
from urllib.parse import unquote, urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Lo que Supabase llama "session pooler". El usuario ahí lleva el
# identificador del proyecto pegado, y ese es el error más común.
HOST_POOLER = "pooler.supabase.com"


def revisar(url: str) -> list[str]:
    """Busca los errores conocidos de una URL de Supabase, sin conectarse."""
    partes = urlparse(url)
    problemas: list[str] = []

    if "+asyncpg" not in (partes.scheme or ""):
        problemas.append(
            "El esquema tiene que ser 'postgresql+asyncpg://'. Con "
            f"'{partes.scheme}://' el sistema ni siquiera carga el driver."
        )

    host = partes.hostname or ""
    if host.startswith("db.") and host.endswith(".supabase.co"):
        problemas.append(
            "Ese es el host de la conexión directa de Supabase, que resuelve "
            "solo a IPv6. Railway sale por IPv4 y falla con 'Network is "
            "unreachable'. Usá el del session pooler."
        )

    usuario = partes.username or ""
    if HOST_POOLER in host and usuario == "postgres":
        problemas.append(
            "El usuario del pooler no es 'postgres' sino "
            "'postgres.<identificador-del-proyecto>'. Ese punto es lo que le "
            "dice al pooler a qué base mandarte; sin él, rechaza la "
            "contraseña aunque sea correcta."
        )

    if HOST_POOLER in host and partes.port == 6543:
        problemas.append(
            "El puerto 6543 es el transaction pooler, que rompe las consultas "
            "preparadas de asyncpg. El session pooler es el 5432."
        )

    clave = partes.password or ""
    if clave and unquote(clave) == clave and any(c in clave for c in "@#/:? "):
        problemas.append(
            "La contraseña tiene caracteres que hay que escapar (@ # / : ? o "
            "espacio). Sin escapar, la dirección se parte en el lugar "
            "equivocado."
        )

    return problemas


def interpretar(fallo: Exception) -> str | None:
    """Traduce los errores conocidos a qué hay que corregir."""
    texto = str(fallo).lower()
    if "password authentication failed" in texto:
        return (
            "La contraseña no es la de esta base. Si el usuario tiene el "
            "identificador del proyecto pegado y aun así falla, reseteala en "
            "Supabase: Project Settings → Database → Reset database password."
        )
    if "tenant or user not found" in texto or "tenant/user" in texto:
        return (
            "El pooler no reconoce el usuario. El identificador que va después "
            "de 'postgres.' es el del proyecto, y lo copiás de la misma "
            "pantalla de Supabase de donde sale la dirección."
        )
    if "network is unreachable" in texto or "nodename nor servname" in texto:
        return (
            "No se llega al host. Si es 'db.<algo>.supabase.co', es la "
            "conexión directa: resuelve solo a IPv6 y hay que usar la del "
            "session pooler."
        )
    if "no module named" in texto:
        return "Falta el driver, casi siempre porque al esquema le falta " "'+asyncpg'."
    return None


async def conectar(url: str) -> None:
    """Se conecta de verdad y cuenta qué pasó."""
    motor = create_async_engine(url)
    try:
        async with motor.connect() as conexion:
            version = (await conexion.execute(text("SELECT version()"))).scalar_one()
        print("✓ Conecta bien.")
        print(f"  {str(version)[:60]}…")
    finally:
        await motor.dispose()


async def principal() -> int:
    """Revisa la URL y trata de conectarse. Devuelve el código de salida."""
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        from app.core.config import settings

        url = settings.database_url
        print("Usando la URL configurada (DATABASE_URL o backend/.env).\n")

    partes = urlparse(url)
    print(f"  usuario  {partes.username}")
    print(f"  host     {partes.hostname}")
    print(f"  puerto   {partes.port}")
    print(f"  base     {(partes.path or '/').lstrip('/')}")
    print(f"  clave    {'(sin contraseña)' if not partes.password else '••• puesta'}\n")

    problemas = revisar(url)
    for problema in problemas:
        print(f"✗ {problema}\n")

    try:
        await conectar(url)
    except Exception as fallo:  # noqa: BLE001 — se muestra el error, sea cual sea
        print(f"✗ No conecta: {type(fallo).__name__}: {fallo}")
        pista = interpretar(fallo)
        if pista is not None:
            print(f"\n  {pista}")
        elif not problemas:
            print(
                "\n  La dirección tiene la forma correcta, así que el "
                "problema está del lado de la base o de la red."
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(principal()))
