"""Sucursales."""

from httpx import AsyncClient

from app.models.sucursal import Sucursal


async def test_cualquier_usuario_lista_sucursales(
    client_vendedor: AsyncClient, sucursal: Sucursal
) -> None:
    """El vendedor las lee: el selector de sucursal está en pantallas suyas."""
    respuesta = await client_vendedor.get("/sucursales")
    assert respuesta.status_code == 200
    assert [s["codigo"] for s in respuesta.json()] == ["TEST"]


async def test_solo_el_admin_da_de_alta_sucursales(
    client_vendedor: AsyncClient,
) -> None:
    """Crear una sucursal es del admin."""
    respuesta = await client_vendedor.post(
        "/sucursales", json={"nombre": "Sucursal Norte", "codigo": "NOR"}
    )
    assert respuesta.status_code == 403


async def test_alta_de_deposito(client_admin: AsyncClient) -> None:
    """El depósito es una sucursal más, con tipo DEPOSITO."""
    respuesta = await client_admin.post(
        "/sucursales",
        json={"nombre": "Depósito", "codigo": "dep", "tipo": "DEPOSITO"},
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["tipo"] == "DEPOSITO"
    # El código se normaliza a mayúsculas para que no convivan "dep" y "DEP".
    assert cuerpo["codigo"] == "DEP"


async def test_no_se_repite_el_codigo(
    client_admin: AsyncClient, sucursal: Sucursal
) -> None:
    """Dos sucursales no pueden compartir el código."""
    respuesta = await client_admin.post(
        "/sucursales", json={"nombre": "Otra", "codigo": "TEST"}
    )
    assert respuesta.status_code == 409


async def test_modificar_sucursal(
    client_admin: AsyncClient, sucursal: Sucursal
) -> None:
    """Se puede corregir la dirección y asignar el punto de venta fiscal."""
    respuesta = await client_admin.patch(
        f"/sucursales/{sucursal.id}",
        json={"direccion": "Av. Siempreviva 742", "punto_venta_arca": 3},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["punto_venta_arca"] == 3
