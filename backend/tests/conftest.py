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
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture
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
from app.models.catalogo import Categoria, Color, CurvaTalle, Marca, Talle
from app.models.producto import Producto
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


async def _abrir_cliente(
    db: AsyncSession, usuario: Usuario | None
) -> AsyncGenerator[AsyncClient, None]:
    """Abre un cliente HTTP propio, opcionalmente ya autenticado.

    Cada fixture de cliente abre **el suyo**. La primera versión de este
    archivo tenía un solo cliente y las fixtures por rol le cambiaban el
    header: un test que pedía `client_admin` y `client_vendedor` a la vez
    recibía el mismo objeto dos veces, con el header del que se hubiera
    resuelto último. Los tests de permisos daban verde sin probar nada — que
    es la peor forma de fallar que puede tener un test.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        if usuario is not None:
            autenticar(ac, usuario)
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP sin sesión iniciada."""
    async for cliente in _abrir_cliente(db, None):
        yield cliente


@pytest_asyncio.fixture
async def client_admin(
    db: AsyncSession, usuario_admin: Usuario
) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP autenticado como administrador."""
    async for cliente in _abrir_cliente(db, usuario_admin):
        yield cliente


@pytest_asyncio.fixture
async def client_encargado(
    db: AsyncSession, usuario_encargado: Usuario
) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP autenticado como encargado."""
    async for cliente in _abrir_cliente(db, usuario_encargado):
        yield cliente


@pytest_asyncio.fixture
async def client_vendedor(
    db: AsyncSession, usuario_vendedor: Usuario
) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP autenticado como vendedor."""
    async for cliente in _abrir_cliente(db, usuario_vendedor):
        yield cliente


# ── Servicios externos ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _sin_r2_real(mocker: MockerFixture) -> MagicMock:
    """Ningún test habla con Cloudflare R2 de verdad.

    `get_cliente_r2` es el único punto del sistema que sale a la red para las
    imágenes, así que mockearlo ahí alcanza para todo. Es una fixture
    automática a propósito: si hubiera que acordarse de pedirla, el día que
    alguien escriba un test de imágenes sin pedirla, la suite empieza a subir
    archivos a un bucket real.
    """
    cliente = MagicMock()

    def _firmar(_metodo: str, **kwargs: object) -> str:
        # Imita la forma de una dirección firmada real: algunos tests miran a
        # qué objeto apunta, no la dirección entera.
        parametros = kwargs["Params"]
        assert isinstance(parametros, dict)
        return f"https://r2.prueba/{parametros['Key']}?X-Amz-Signature=simulada"

    cliente.generate_presigned_url.side_effect = _firmar
    mocker.patch("app.services.r2_service.esta_configurado", return_value=True)
    return mocker.patch("app.services.r2_service.get_cliente_r2", return_value=cliente)


# ── Catálogo ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def curva_remeras(db: AsyncSession) -> CurvaTalle:
    """Una curva de talles de remera, con el orden ya puesto."""
    curva = CurvaTalle(nombre="Remeras", activa=True)
    db.add(curva)
    await db.flush()
    for orden, valor in enumerate(["S", "M", "L", "XL"]):
        db.add(Talle(curva_talle_id=curva.id, valor=valor, orden=orden, activo=True))
    await db.flush()
    await db.refresh(curva)
    return curva


@pytest_asyncio.fixture
async def curva_calzado(db: AsyncSession) -> CurvaTalle:
    """Una curva de calzado, para probar que los talles no se mezclan."""
    curva = CurvaTalle(nombre="Calzado", activa=True)
    db.add(curva)
    await db.flush()
    for orden, valor in enumerate(["38", "39", "40"]):
        db.add(Talle(curva_talle_id=curva.id, valor=valor, orden=orden, activo=True))
    await db.flush()
    await db.refresh(curva)
    return curva


@pytest_asyncio.fixture
async def categoria(db: AsyncSession, curva_remeras: CurvaTalle) -> Categoria:
    """La categoría Remeras, con la curva de remeras."""
    categoria = Categoria(
        nombre="Remeras", curva_talle_id=curva_remeras.id, activa=True
    )
    db.add(categoria)
    await db.flush()
    await db.refresh(categoria)
    return categoria


@pytest_asyncio.fixture
async def marca(db: AsyncSession) -> Marca:
    """Una marca de prueba."""
    marca = Marca(nombre="Nike", activa=True)
    db.add(marca)
    await db.flush()
    return marca


@pytest_asyncio.fixture
async def color_negro(db: AsyncSession) -> Color:
    """Color negro."""
    color = Color(nombre="Negro", codigo_hex="#000000", activo=True)
    db.add(color)
    await db.flush()
    return color


@pytest_asyncio.fixture
async def color_blanco(db: AsyncSession) -> Color:
    """Color blanco."""
    color = Color(nombre="Blanco", codigo_hex="#FFFFFF", activo=True)
    db.add(color)
    await db.flush()
    return color


@pytest_asyncio.fixture
async def producto(db: AsyncSession, categoria: Categoria, marca: Marca) -> Producto:
    """Una remera, todavía sin variantes."""
    producto = Producto(
        nombre="Remera lisa",
        categoria_id=categoria.id,
        marca_id=marca.id,
        activo=True,
    )
    db.add(producto)
    await db.flush()
    await db.refresh(producto)
    return producto
