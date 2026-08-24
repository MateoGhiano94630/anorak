"""Ingreso al sistema y sesión."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario
from tests.conftest import PASSWORD_DE_PRUEBA, autenticar


async def test_health_no_pide_sesion(client: AsyncClient) -> None:
    """El chequeo de vida contesta sin autenticación (lo llama Railway)."""
    respuesta = await client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


async def test_login_correcto_devuelve_token_y_usuario(
    client: AsyncClient, usuario_admin: Usuario
) -> None:
    """Con las credenciales correctas se entra y vuelven los datos del usuario."""
    respuesta = await client.post(
        "/auth/login",
        json={"email": usuario_admin.email, "password": PASSWORD_DE_PRUEBA},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["access_token"]
    assert cuerpo["usuario"]["email"] == usuario_admin.email
    assert cuerpo["usuario"]["rol"] == "ADMIN"


async def test_login_con_password_incorrecta_no_entra(
    client: AsyncClient, usuario_admin: Usuario
) -> None:
    """Una contraseña equivocada da 401."""
    respuesta = await client.post(
        "/auth/login",
        json={"email": usuario_admin.email, "password": "otracosa123"},
    )
    assert respuesta.status_code == 401


async def test_login_con_email_inexistente_da_el_mismo_error(
    client: AsyncClient,
) -> None:
    """El mensaje no distingue email inexistente de contraseña equivocada.

    Si distinguiera, el formulario de ingreso serviría para averiguar qué
    direcciones tienen cuenta en el sistema.
    """
    respuesta = await client.post(
        "/auth/login", json={"email": "nadie@prueba.com.ar", "password": "loquesea123"}
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Email o contraseña incorrectos"


async def test_usuario_dado_de_baja_no_entra(
    client: AsyncClient, usuario_vendedor: Usuario, db: AsyncSession
) -> None:
    """Una cuenta inactiva no puede iniciar sesión."""
    usuario_vendedor.activo = False
    await db.flush()
    respuesta = await client.post(
        "/auth/login",
        json={"email": usuario_vendedor.email, "password": PASSWORD_DE_PRUEBA},
    )
    assert respuesta.status_code == 403


async def test_me_sin_token_da_401(client: AsyncClient) -> None:
    """Sin token no se lee nada."""
    assert (await client.get("/auth/me")).status_code == 401


async def test_me_con_token_invalido_da_401(client: AsyncClient) -> None:
    """Un token que no valida da 401, no un error del servidor."""
    client.headers["Authorization"] = "Bearer esto-no-es-un-token"
    assert (await client.get("/auth/me")).status_code == 401


async def test_me_devuelve_al_usuario_de_la_sesion(
    client_admin: AsyncClient, usuario_admin: Usuario
) -> None:
    """Con token válido, /auth/me dice quién está usando el sistema."""
    respuesta = await client_admin.get("/auth/me")
    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == usuario_admin.email


async def test_login_registra_el_ultimo_ingreso(
    client: AsyncClient, usuario_admin: Usuario, db: AsyncSession
) -> None:
    """Cada ingreso deja marcada la fecha, que es dato de auditoría."""
    assert usuario_admin.ultimo_ingreso is None
    await client.post(
        "/auth/login",
        json={"email": usuario_admin.email, "password": PASSWORD_DE_PRUEBA},
    )
    await db.refresh(usuario_admin)
    assert usuario_admin.ultimo_ingreso is not None


async def test_cambiar_password_propia(
    client: AsyncClient, usuario_vendedor: Usuario
) -> None:
    """Quien conoce su contraseña actual puede cambiarla y entra con la nueva."""
    autenticar(client, usuario_vendedor)
    respuesta = await client.post(
        "/auth/cambiar-password",
        json={"password_actual": PASSWORD_DE_PRUEBA, "password_nueva": "nuevaclave99"},
    )
    assert respuesta.status_code == 200

    del client.headers["Authorization"]
    reingreso = await client.post(
        "/auth/login",
        json={"email": usuario_vendedor.email, "password": "nuevaclave99"},
    )
    assert reingreso.status_code == 200


async def test_cambiar_password_con_la_actual_equivocada_falla(
    client: AsyncClient, usuario_vendedor: Usuario
) -> None:
    """No se puede cambiar la contraseña sin saber la anterior."""
    autenticar(client, usuario_vendedor)
    respuesta = await client.post(
        "/auth/cambiar-password",
        json={"password_actual": "loquesea123", "password_nueva": "nuevaclave99"},
    )
    assert respuesta.status_code == 400
