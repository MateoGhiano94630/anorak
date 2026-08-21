"""Marcas, curvas de talle, colores y categorías."""

from httpx import AsyncClient

from app.models.catalogo import Categoria, CurvaTalle, Marca


async def test_el_vendedor_lee_el_catalogo_pero_no_lo_edita(
    client_vendedor: AsyncClient, marca: Marca
) -> None:
    """El mostrador necesita ver marcas y talles; cargarlos es del encargado."""
    assert (await client_vendedor.get("/marcas")).status_code == 200
    respuesta = await client_vendedor.post("/marcas", json={"nombre": "Adidas"})
    assert respuesta.status_code == 403


async def test_alta_de_marca(client_admin: AsyncClient) -> None:
    """Se da de alta una marca."""
    respuesta = await client_admin.post("/marcas", json={"nombre": "  Adidas  "})
    assert respuesta.status_code == 201
    # Los espacios de más se sacan: si no, "Adidas" y "Adidas " conviven como
    # dos marcas y el índice único no las detecta.
    assert respuesta.json()["nombre"] == "Adidas"


async def test_no_se_repite_la_marca(client_admin: AsyncClient, marca: Marca) -> None:
    """Dos marcas no pueden llamarse igual."""
    respuesta = await client_admin.post("/marcas", json={"nombre": marca.nombre})
    assert respuesta.status_code == 409


async def test_alta_de_curva_con_sus_talles(client_admin: AsyncClient) -> None:
    """Una curva se carga con todos sus talles de una vez."""
    respuesta = await client_admin.post(
        "/curvas-talle",
        json={
            "nombre": "Pantalones",
            "talles": [{"valor": "38"}, {"valor": "40"}, {"valor": "42"}],
        },
    )
    assert respuesta.status_code == 201
    assert [t["valor"] for t in respuesta.json()["talles"]] == ["38", "40", "42"]


async def test_los_talles_conservan_el_orden_de_carga(
    client_admin: AsyncClient,
) -> None:
    """S, M, L, XL salen en ese orden y no en el alfabético.

    Ordenados por nombre, L va antes que M y XS antes que XXL, que es al revés
    de como los busca cualquiera en el mostrador.
    """
    await client_admin.post(
        "/curvas-talle",
        json={
            "nombre": "Buzos",
            "talles": [{"valor": "S"}, {"valor": "M"}, {"valor": "L"}, {"valor": "XL"}],
        },
    )
    curvas = (await client_admin.get("/curvas-talle")).json()
    buzos = next(curva for curva in curvas if curva["nombre"] == "Buzos")
    assert [t["valor"] for t in buzos["talles"]] == ["S", "M", "L", "XL"]


async def test_una_curva_no_puede_tener_talles_repetidos(
    client_admin: AsyncClient,
) -> None:
    """Dos talles iguales en la misma curva no tienen sentido."""
    respuesta = await client_admin.post(
        "/curvas-talle",
        json={"nombre": "Rara", "talles": [{"valor": "M"}, {"valor": "M"}]},
    )
    assert respuesta.status_code == 400


async def test_una_curva_sin_talles_no_se_puede_cargar(
    client_admin: AsyncClient,
) -> None:
    """Una curva vacía dejaría una categoría que no admite ningún talle."""
    respuesta = await client_admin.post(
        "/curvas-talle", json={"nombre": "Vacia", "talles": []}
    )
    assert respuesta.status_code == 422


async def test_agregar_un_talle_a_una_curva_existente(
    client_admin: AsyncClient, curva_remeras: CurvaTalle
) -> None:
    """Se puede sumar un talle sin rehacer la curva."""
    respuesta = await client_admin.post(
        f"/curvas-talle/{curva_remeras.id}/talles", json={"valor": "XXL"}
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["orden"] == 4


async def test_no_se_repite_el_talle_dentro_de_la_curva(
    client_admin: AsyncClient, curva_remeras: CurvaTalle
) -> None:
    """El mismo talle dos veces en la misma curva se rechaza."""
    respuesta = await client_admin.post(
        f"/curvas-talle/{curva_remeras.id}/talles", json={"valor": "M"}
    )
    assert respuesta.status_code == 409


async def test_alta_de_color_con_su_tono(client_admin: AsyncClient) -> None:
    """El color puede llevar su tono para mostrarlo en pantalla."""
    respuesta = await client_admin.post(
        "/colores", json={"nombre": "Azul marino", "codigo_hex": "#1B2A4A"}
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["codigo_hex"] == "#1B2A4A"


async def test_un_tono_mal_escrito_se_rechaza(client_admin: AsyncClient) -> None:
    """El tono tiene que ser un color en formato #RRGGBB."""
    respuesta = await client_admin.post(
        "/colores", json={"nombre": "Raro", "codigo_hex": "azulito"}
    )
    assert respuesta.status_code == 422


async def test_la_categoria_trae_el_nombre_de_su_curva(
    client_admin: AsyncClient, categoria: Categoria
) -> None:
    """El listado dice qué talles usa cada categoría sin pedirlo aparte."""
    respuesta = await client_admin.get("/categorias")
    assert respuesta.status_code == 200
    assert respuesta.json()[0]["curva_nombre"] == "Remeras"


async def test_una_categoria_necesita_una_curva_que_exista(
    client_admin: AsyncClient,
) -> None:
    """No se puede apuntar a una curva inventada."""
    respuesta = await client_admin.post(
        "/categorias",
        json={
            "nombre": "Inventada",
            "curva_talle_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert respuesta.status_code == 400
