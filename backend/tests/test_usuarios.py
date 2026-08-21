"""Administración de usuarios."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sucursal import Sucursal
from app.models.usuario import RolUsuario, Usuario


async def test_admin_da_de_alta_un_usuario(
    client_admin: AsyncClient, sucursal: Sucursal
) -> None:
    """El admin crea cuentas."""
    respuesta = await client_admin.post(
        "/usuarios",
        json={
            "nombre": "Sofía Vendedora",
            "email": "Sofia@Prueba.com.ar",
            "password": "clave12345",
            "rol": "VENDEDOR",
            "sucursal_id": str(sucursal.id),
        },
    )
    assert respuesta.status_code == 201
    # El email se guarda en minúsculas: si no, "Sofia@" y "sofia@" conviven
    # como dos cuentas y el índice único no las detecta.
    assert respuesta.json()["email"] == "sofia@prueba.com.ar"


async def test_no_se_repite_el_email(
    client_admin: AsyncClient, usuario_admin: Usuario
) -> None:
    """Dos cuentas no pueden compartir email."""
    respuesta = await client_admin.post(
        "/usuarios",
        json={
            "nombre": "Otro",
            "email": usuario_admin.email,
            "password": "clave12345",
            "rol": "VENDEDOR",
        },
    )
    assert respuesta.status_code == 409


async def test_el_vendedor_no_administra_usuarios(client_vendedor: AsyncClient) -> None:
    """Solo el admin entra a la administración de cuentas."""
    assert (await client_vendedor.get("/usuarios")).status_code == 403


async def test_password_corta_no_pasa(client_admin: AsyncClient) -> None:
    """La contraseña tiene un mínimo de ocho caracteres."""
    respuesta = await client_admin.post(
        "/usuarios",
        json={
            "nombre": "Corta",
            "email": "corta@prueba.com.ar",
            "password": "1234",
            "rol": "VENDEDOR",
        },
    )
    assert respuesta.status_code == 422


async def test_la_lista_de_usuarios_no_expone_el_hash(
    client_admin: AsyncClient, usuario_vendedor: Usuario
) -> None:
    """El hash de contraseña no sale nunca por la API."""
    respuesta = await client_admin.get("/usuarios")
    assert respuesta.status_code == 200
    for usuario in respuesta.json():
        assert "password_hash" not in usuario


async def test_dar_de_baja_es_desactivar_no_borrar(
    client_admin: AsyncClient, usuario_vendedor: Usuario
) -> None:
    """La baja es lógica: la cuenta sigue existiendo como autor de movimientos."""
    respuesta = await client_admin.patch(
        f"/usuarios/{usuario_vendedor.id}", json={"activo": False}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
    assert (
        await client_admin.get(f"/usuarios/{usuario_vendedor.id}")
    ).status_code == 200


async def test_el_admin_no_puede_darse_de_baja_a_si_mismo(
    client_admin: AsyncClient, usuario_admin: Usuario
) -> None:
    """Evita dejar el sistema sin nadie que lo administre."""
    respuesta = await client_admin.patch(
        f"/usuarios/{usuario_admin.id}", json={"activo": False}
    )
    assert respuesta.status_code == 400


async def test_el_rol_leido_de_la_base_vuelve_como_enum(
    db: AsyncSession, usuario_vendedor: Usuario
) -> None:
    """Una fila traída de la base tiene el rol como enum, no como texto suelto.

    Es la diferencia entre `Mapped[RolUsuario]` siendo verdad o siendo una
    anotación decorativa. Con la columna declarada como `String` a secas, el
    objeto recién creado en Python conserva el enum —así que los tests pasan—
    y el traído de la base devuelve `str`: cualquier `.value` explota recién
    en producción. Pasó exactamente eso al probar el ingreso a mano.
    """
    db.expunge_all()
    leido = await db.get(Usuario, usuario_vendedor.id)
    assert leido is not None
    assert isinstance(leido.rol, RolUsuario)
    assert leido.rol.value == "VENDEDOR"
