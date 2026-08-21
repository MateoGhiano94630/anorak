"""Precios y su historial."""

from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogo import Color, CurvaTalle
from app.models.precio import Precio
from app.models.producto import Producto
from app.services import precio_service


async def _variante_de(
    client: AsyncClient, producto: Producto, curva: CurvaTalle, color: Color
) -> str:
    """Crea una variante del producto y devuelve su identificador."""
    respuesta = await client.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(curva.talles[0].id)],
            "color_ids": [str(color.id)],
        },
    )
    return str(respuesta.json()["variantes"][0]["id"])


async def test_una_variante_nace_sin_precio(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """Primero entra al catálogo y después se le pone precio.

    Sin precio, el punto de venta se va a negar a venderla. Es preferible a
    tomarla como si valiera cero.
    """
    await _variante_de(client_admin, producto, curva_remeras, color_negro)
    detalle = (await client_admin.get(f"/productos/{producto.id}")).json()
    assert detalle["variantes"][0]["precio_venta"] is None


async def test_poner_un_precio(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """Se carga el precio de venta y el costo."""
    variante_id = await _variante_de(client_admin, producto, curva_remeras, color_negro)
    respuesta = await client_admin.post(
        f"/variantes/{variante_id}/precio",
        json={"precio_venta": "18500.00", "costo": "9200.50", "motivo": "Lista nueva"},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["vigente_hasta"] is None


async def test_los_importes_viajan_como_texto(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """El JSON manda "18500.00", no el número 18500.0.

    Los decimales de JavaScript no representan exactamente los centavos, y esa
    diferencia aparece sumada en un cierre de caja.
    """
    variante_id = await _variante_de(client_admin, producto, curva_remeras, color_negro)
    respuesta = await client_admin.post(
        f"/variantes/{variante_id}/precio", json={"precio_venta": "18500.55"}
    )
    assert respuesta.json()["precio_venta"] == "18500.55"


async def test_cambiar_el_precio_cierra_el_anterior(
    client_admin: AsyncClient,
    db: AsyncSession,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """El precio viejo no se pisa: se le pone fecha de fin.

    Así una venta de marzo se puede explicar con el precio que regía en marzo,
    aunque hoy sea otro.
    """
    variante_id = await _variante_de(client_admin, producto, curva_remeras, color_negro)
    await client_admin.post(
        f"/variantes/{variante_id}/precio", json={"precio_venta": "10000.00"}
    )
    await client_admin.post(
        f"/variantes/{variante_id}/precio",
        json={"precio_venta": "12000.00", "motivo": "Aumento del proveedor"},
    )

    historial = (await client_admin.get(f"/variantes/{variante_id}/precios")).json()
    assert len(historial) == 2
    assert historial[0]["precio_venta"] == "12000.00"
    assert historial[0]["vigente_hasta"] is None
    assert historial[1]["precio_venta"] == "10000.00"
    assert historial[1]["vigente_hasta"] is not None


async def test_la_base_no_admite_dos_precios_vigentes(
    client_admin: AsyncClient,
    db: AsyncSession,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """El índice único parcial es la última red, por debajo del código.

    Si un día un cambio de precio se escribe mal y no cierra el anterior, la
    base lo rechaza en vez de dejar una variante con dos precios y que el
    mostrador cobre cualquiera de los dos.
    """
    from sqlalchemy.exc import IntegrityError

    variante_id = await _variante_de(client_admin, producto, curva_remeras, color_negro)
    await client_admin.post(
        f"/variantes/{variante_id}/precio", json={"precio_venta": "10000.00"}
    )
    db.add(Precio(variante_id=variante_id, precio_venta=Decimal("9999.00")))
    try:
        await db.flush()
    except IntegrityError:
        return
    raise AssertionError("La base aceptó dos precios vigentes para la misma variante")


async def test_precio_para_todo_el_producto(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
    color_blanco: Color,
) -> None:
    """Una remera vale lo mismo en S que en L: se carga una vez."""
    await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(t.id) for t in curva_remeras.talles],
            "color_ids": [str(color_negro.id), str(color_blanco.id)],
        },
    )
    respuesta = await client_admin.post(
        f"/productos/{producto.id}/precio", json={"precio_venta": "21000.00"}
    )
    assert respuesta.status_code == 201
    assert len(respuesta.json()) == 8

    detalle = (await client_admin.get(f"/productos/{producto.id}")).json()
    assert all(v["precio_venta"] == "21000.00" for v in detalle["variantes"])


async def test_el_listado_muestra_el_rango_de_precios(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """Si un talle vale distinto, el listado lo muestra como un rango."""
    creadas = await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(t.id) for t in curva_remeras.talles[:2]],
            "color_ids": [str(color_negro.id)],
        },
    )
    variantes = creadas.json()["variantes"]
    await client_admin.post(
        f"/variantes/{variantes[0]['id']}/precio", json={"precio_venta": "10000.00"}
    )
    await client_admin.post(
        f"/variantes/{variantes[1]['id']}/precio", json={"precio_venta": "15000.00"}
    )

    fila = (await client_admin.get("/productos")).json()[0]
    assert fila["precio_desde"] == "10000.00"
    assert fila["precio_hasta"] == "15000.00"


async def test_el_encargado_no_cambia_precios(
    client_encargado: AsyncClient,
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """En un local de ropa el margen es el negocio: la lista la toca el dueño."""
    variante_id = await _variante_de(client_admin, producto, curva_remeras, color_negro)
    respuesta = await client_encargado.post(
        f"/variantes/{variante_id}/precio", json={"precio_venta": "1.00"}
    )
    assert respuesta.status_code == 403


async def test_un_precio_negativo_se_rechaza(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """Ninguna prenda vale menos que cero."""
    variante_id = await _variante_de(client_admin, producto, curva_remeras, color_negro)
    respuesta = await client_admin.post(
        f"/variantes/{variante_id}/precio", json={"precio_venta": "-100.00"}
    )
    assert respuesta.status_code == 422


async def test_el_precio_se_guarda_con_decimales_exactos(
    db: AsyncSession,
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """Lo que se guarda es Decimal, no punto flotante."""
    variante_id = await _variante_de(client_admin, producto, curva_remeras, color_negro)
    await client_admin.post(
        f"/variantes/{variante_id}/precio", json={"precio_venta": "18500.55"}
    )
    import uuid as _uuid

    vigente = await precio_service.precio_vigente(db, _uuid.UUID(variante_id))
    assert vigente is not None
    assert vigente.precio_venta == Decimal("18500.55")
