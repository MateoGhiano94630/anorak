"""Punto de entrada de la API."""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.audit_log import router as audit_log_router
from app.api.auth import router as auth_router
from app.api.catalogo import (
    categorias_router,
    colores_router,
    curvas_router,
    marcas_router,
)
from app.api.precios import router as precios_router
from app.api.productos import router as productos_router
from app.api.productos import variantes_router
from app.api.stock import router as stock_router
from app.api.sucursales import router as sucursales_router
from app.api.usuarios import router as usuarios_router
from app.core import (
    audit as _audit,  # noqa: F401 — importarlo registra el listener de auditoría
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
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
    """Deja la base con los datos mínimos y avisa si falta migrar.

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
app.include_router(sucursales_router)
app.include_router(marcas_router)
app.include_router(curvas_router)
app.include_router(colores_router)
app.include_router(categorias_router)
app.include_router(productos_router)
app.include_router(variantes_router)
app.include_router(precios_router)
app.include_router(stock_router)
app.include_router(audit_log_router)


@app.get("/health", tags=["sistema"])
async def health() -> dict[str, str]:
    """Chequeo de vida para Railway."""
    return {"estado": "ok", "version": app.version}
