"""
Infraestructura común de los tests.

Reglas que sostiene este archivo:

- La base es **SQLite en memoria**, una por test. No hace falta `.env`, ni
  Docker, ni PostgreSQL: `pytest` corre en una máquina recién clonada.
- Ningún test sale a la red. Los servicios externos (ARCA, R2) se mockean.
- No hay fixture `event_loop`: está deprecada en pytest-asyncio moderno y
  definirla vuelve a romper la suite en cada actualización.
"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core import database
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.sucursal import Sucursal, TipoSucursal
from app.models.usuario import RolUsuario, Usuario

PASSWORD_DE_PRUEBA = "prueba1234"


@pytest_asyncio.fixture
async def engine_test() -> AsyncGenerator[AsyncEngine, None]:
    """Una base SQLite en memoria por test, creada desde los modelos.

    `StaticPool` más `check_same_thread=False` hacen que todas las sesiones
    del test compartan la misma conexión: sin eso, cada conexión nueva a
    `:memory:` abre una base vacía distinta y no se ve nada de lo escrito.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(engine_test: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Sesión de base para usar directamente desde un test."""
    session_maker = async_sessionmaker(
        engine_test, class_=AsyncSession, expire_on_commit=False
    )
    # El código que abre su propia sesión (tareas de fondo, sincronización)
    # no recibe la inyectada por get_db. Sin esta línea terminaría hablando
    # con la base real configurada en el entorno.
    original = database.AsyncSessionLocal
    database.AsyncSessionLocal = session_maker
    async with session_maker() as session:
        yield session
        await session.rollback()
    database.AsyncSessionLocal = original


@pytest_asyncio.fixture
async def sucursal(db: AsyncSession) -> Sucursal:
    """La sucursal contra la que se prueban stock, caja y ventas."""
    sucursal = Sucursal(
        nombre="Local de prueba", codigo="TEST", tipo=TipoSucursal.local, activa=True
    )
    db.add(sucursal)
    await db.flush()
    return sucursal


async def _crear_usuario(
    db: AsyncSession, nombre: str, email: str, rol: RolUsuario, sucursal: Sucursal
) -> Usuario:
    """Da de alta un usuario de prueba con la contraseña estándar."""
    usuario = Usuario(
        nombre=nombre,
        email=email,
        password_hash=hash_password(PASSWORD_DE_PRUEBA),
        rol=rol,
        sucursal_id=sucursal.id,
        activo=True,
    )
    db.add(usuario)
    await db.flush()
    return usuario


@pytest_asyncio.fixture
async def usuario_admin(db: AsyncSession, sucursal: Sucursal) -> Usuario:
    """Usuario con rol admin."""
    return await _crear_usuario(
        db, "Admin Prueba", "admin@prueba.com.ar", RolUsuario.admin, sucursal
    )


@pytest_asyncio.fixture
async def usuario_encargado(db: AsyncSession, sucursal: Sucursal) -> Usuario:
    """Usuario con rol encargado."""
    return await _crear_usuario(
        db,
        "Encargado Prueba",
        "encargado@prueba.com.ar",
        RolUsuario.encargado,
        sucursal,
    )


@pytest_asyncio.fixture
async def usuario_vendedor(db: AsyncSession, sucursal: Sucursal) -> Usuario:
    """Usuario con rol vendedor."""
    return await _crear_usuario(
        db, "Vendedor Prueba", "vendedor@prueba.com.ar", RolUsuario.vendedor, sucursal
    )


def token_de(usuario: Usuario) -> str:
    """Arma un token válido para el usuario indicado."""
    return create_access_token(
        {"sub": str(usuario.id), "email": usuario.email, "rol": usuario.rol.value}
    )


def autenticar(cliente: AsyncClient, usuario: Usuario) -> AsyncClient:
    """Deja el cliente HTTP hablando como el usuario indicado."""
    cliente.headers["Authorization"] = f"Bearer {token_de(usuario)}"
    return cliente


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP contra la API, con la base del test inyectada."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_admin(client: AsyncClient, usuario_admin: Usuario) -> AsyncClient:
    """Cliente HTTP autenticado como admin."""
    return autenticar(client, usuario_admin)


@pytest_asyncio.fixture
async def client_vendedor(
    client: AsyncClient, usuario_vendedor: Usuario
) -> AsyncClient:
    """Cliente HTTP autenticado como vendedor."""
    return autenticar(client, usuario_vendedor)
