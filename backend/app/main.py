"""Punto de entrada de la API."""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.audit_log import router as audit_log_router
from app.api.auth import router as auth_router
from app.api.caja import medios_router
from app.api.caja import router as caja_router
from app.api.usuarios import router as usuarios_router
from app.api.ventas import articulos_router
from app.api.ventas import router as ventas_router
from app.core import (
    audit as _audit,  # noqa: F401 — importarlo registra el listener de auditoría
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.diagnostico import medir_tiempos
from app.core.schema_check import verificar_esquema_al_dia
from app.services import seed_service

# Sin esta configuración, un logger sin handler propio no imprime nada por
# debajo de WARNING y ni siquiera el WARNING es seguro que salga. stdout
# explícito es lo que Railway captura sin ambigüedad.
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logging.getLogger("app").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Deja la base con la cuenta inicial y avisa si falta migrar.

    Si la base no responde, el seed se saltea con un log y la API levanta
    igual: un problema de conexión no puede dejar a Railway sin health check.
    """
    try:
        async with AsyncSessionLocal() as db:
            await seed_service.seed_inicial(db)
    except Exception:
        logger.exception("Seed inicial omitido — la API arranca igual")
    await verificar_esquema_al_dia()
    yield


app = FastAPI(
    title="Anorak — gestión de local de ropa",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(medios_router)
app.include_router(caja_router)
app.include_router(articulos_router)
app.include_router(ventas_router)
app.include_router(audit_log_router)


@app.get("/health", tags=["sistema"])
async def health() -> dict[str, str]:
    """Chequeo de vida para Railway.

    No toca la base a propósito, aunque la tentación de medirla acá sea obvia:
    si el health check dependiera de la base, un rato de Supabase caído haría
    que Railway diera el despliegue por muerto y lo reiniciara en loop. La
    medición vive en `/diagnostico`, que no es un health check de nadie.
    """
    return {"estado": "ok", "version": app.version}


@app.get("/diagnostico", tags=["sistema"])
async def diagnostico() -> dict[str, Any]:
    """Dice a dónde se va el tiempo de un ingreso, medido desde el servidor.

    Abrila en el navegador cuando el sistema esté lento. Devuelve cuánto tarda
    este servidor en abrir una conexión con la base, cuánto tarda un viaje de
    ida y vuelta hasta ella, y cuánto tarda un bcrypt en esta máquina.

    Es pública, y tiene que serlo: sirve justamente cuando no se puede entrar,
    así que pedirle sesión la volvería inútil. No expone nada secreto —números,
    el nombre del entorno y el host de la base, sin usuario ni contraseña—,
    pero es una herramienta de diagnóstico y no una parte del sistema: cuando
    el problema esté resuelto, esto se borra.
    """
    return await medir_tiempos()
