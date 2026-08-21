"""Productos, variantes e imágenes."""

import io

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogo import Categoria, Color, CurvaTalle, Marca
from app.models.producto import Producto, Variante


async def test_alta_de_producto(
    client_admin: AsyncClient, categoria: Categoria, marca: Marca
) -> None:
    """Un producto se da de alta sin variantes: primero el molde."""
    respuesta = await client_admin.post(
        "/productos",
        json={
            "nombre": "Remera estampada",
            "categoria_id": str(categoria.id),
            "marca_id": str(marca.id),
            "genero": "UNISEX",
            "temporada": "VERANO",
        },
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["variantes"] == []
    assert cuerpo["categoria"] == "Remeras"
    assert cuerpo["marca"] == "Nike"


async def test_generar_variantes_arma_todas_las_combinaciones(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
    color_blanco: Color,
) -> None:
    """Cuatro talles por dos colores son ocho variantes, de una sola vez.

    Cargarlas de a una es lo que hace que alguien se saltee el talle L y no se
    entere hasta que un cliente lo pide.
    """
    respuesta = await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(t.id) for t in curva_remeras.talles],
            "color_ids": [str(color_negro.id), str(color_blanco.id)],
        },
    )
    assert respuesta.status_code == 201
    variantes = respuesta.json()["variantes"]
    assert len(variantes) == 8
    assert {(v["talle"], v["color"]) for v in variantes} == {
        (talle, color)
        for talle in ["S", "M", "L", "XL"]
        for color in ["Negro", "Blanco"]
    }


async def test_las_variantes_salen_en_el_orden_de_la_curva(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """El detalle de un producto muestra S, M, L, XL en ese orden."""
    await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(t.id) for t in curva_remeras.talles],
            "color_ids": [str(color_negro.id)],
        },
    )
    detalle = (await client_admin.get(f"/productos/{producto.id}")).json()
    assert [v["talle"] for v in detalle["variantes"]] == ["S", "M", "L", "XL"]


async def test_no_se_puede_usar_un_talle_de_otra_curva(
    client_admin: AsyncClient,
    producto: Producto,
    curva_calzado: CurvaTalle,
    color_negro: Color,
) -> None:
    """Una remera en talle 38 se rechaza.

    Es para lo que sirve que la categoría tenga curva: sin eso, el catálogo se
    llena de combinaciones que no existen en la realidad.
    """
    respuesta = await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(curva_calzado.talles[0].id)],
            "color_ids": [str(color_negro.id)],
        },
    )
    assert respuesta.status_code == 400
    assert "curva" in respuesta.json()["detail"]


async def test_volver_a_generar_no_duplica_lo_que_ya_estaba(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
    color_blanco: Color,
) -> None:
    """Sumar un color a un producto ya cargado no repite las variantes viejas."""
    talles = [str(t.id) for t in curva_remeras.talles]
    await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={"talle_ids": talles, "color_ids": [str(color_negro.id)]},
    )
    respuesta = await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": talles,
            "color_ids": [str(color_negro.id), str(color_blanco.id)],
        },
    )
    assert len(respuesta.json()["variantes"]) == 8


async def test_cada_variante_sale_con_un_codigo_distinto(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
    color_blanco: Color,
) -> None:
    """Los códigos internos no se repiten ni siquiera dentro de la misma tanda."""
    respuesta = await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(t.id) for t in curva_remeras.talles],
            "color_ids": [str(color_negro.id), str(color_blanco.id)],
        },
    )
    codigos = [v["sku"] for v in respuesta.json()["variantes"]]
    assert len(set(codigos)) == len(codigos)
    assert codigos[0].startswith("NIKREMLIS")


async def test_dos_productos_parecidos_no_generan_el_mismo_codigo(
    client_admin: AsyncClient,
    db: AsyncSession,
    producto: Producto,
    categoria: Categoria,
    marca: Marca,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """ "Remera lisa" y "Remera estampada" tienen que distinguirse.

    Si el código saliera de las primeras letras del nombre entero, los dos
    quedarían como REMER y solo se diferenciarían por el número que el
    sistema agrega al final. Dejaría de servir para reconocer la prenda, que
    es para lo único que está.
    """
    otro = Producto(
        nombre="Remera estampada",
        categoria_id=categoria.id,
        marca_id=marca.id,
        activo=True,
    )
    db.add(otro)
    await db.flush()

    cuerpo = {
        "talle_ids": [str(curva_remeras.talles[0].id)],
        "color_ids": [str(color_negro.id)],
    }
    lisa = await client_admin.post(f"/productos/{producto.id}/variantes", json=cuerpo)
    estampada = await client_admin.post(f"/productos/{otro.id}/variantes", json=cuerpo)

    codigo_lisa = lisa.json()["variantes"][0]["sku"]
    codigo_estampada = estampada.json()["variantes"][0]["sku"]
    assert codigo_lisa == "NIKREMLIS-S-NEG"
    assert codigo_estampada == "NIKREMEST-S-NEG"


async def test_el_codigo_no_lleva_acentos(
    client_admin: AsyncClient,
    db: AsyncSession,
    categoria: Categoria,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """ "Niño" y "Nino" no pueden generar códigos distintos para lo mismo."""
    producto = Producto(nombre="Remera niño", categoria_id=categoria.id, activo=True)
    db.add(producto)
    await db.flush()
    respuesta = await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(curva_remeras.talles[0].id)],
            "color_ids": [str(color_negro.id)],
        },
    )
    codigo = respuesta.json()["variantes"][0]["sku"]
    assert codigo.isascii()
    assert "REMNIN" in codigo


async def test_buscar_una_prenda_por_su_codigo(
    client_vendedor: AsyncClient,
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """El mostrador ubica la prenda pasando el código de la etiqueta."""
    creadas = await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(curva_remeras.talles[1].id)],
            "color_ids": [str(color_negro.id)],
        },
    )
    codigo = creadas.json()["variantes"][0]["sku"]

    respuesta = await client_vendedor.get(
        "/variantes/buscar", params={"codigo": codigo}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["talle"] == "M"


async def test_buscar_tambien_encuentra_por_codigo_de_barras(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """No toda la ropa trae código de barras, pero cuando lo trae se usa."""
    creadas = await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(curva_remeras.talles[0].id)],
            "color_ids": [str(color_negro.id)],
        },
    )
    variante_id = creadas.json()["variantes"][0]["id"]
    await client_admin.patch(
        f"/variantes/{variante_id}", json={"codigo_barras": "7791234567890"}
    )
    respuesta = await client_admin.get(
        "/variantes/buscar", params={"codigo": "7791234567890"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == variante_id


async def test_un_codigo_que_no_existe_avisa_con_claridad(
    client_vendedor: AsyncClient,
) -> None:
    """El mensaje lo lee quien atiende, así que dice qué pasó."""
    respuesta = await client_vendedor.get("/variantes/buscar", params={"codigo": "XXX"})
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No hay ninguna prenda con ese código"


async def test_dos_variantes_no_pueden_compartir_el_codigo_de_barras(
    client_admin: AsyncClient,
    producto: Producto,
    curva_remeras: CurvaTalle,
    color_negro: Color,
) -> None:
    """El código de barras identifica una prenda concreta."""
    creadas = await client_admin.post(
        f"/productos/{producto.id}/variantes",
        json={
            "talle_ids": [str(t.id) for t in curva_remeras.talles[:2]],
            "color_ids": [str(color_negro.id)],
        },
    )
    primera, segunda = creadas.json()["variantes"][:2]
    await client_admin.patch(
        f"/variantes/{primera['id']}", json={"codigo_barras": "7790000000001"}
    )
    respuesta = await client_admin.patch(
        f"/variantes/{segunda['id']}", json={"codigo_barras": "7790000000001"}
    )
    assert respuesta.status_code == 409


async def test_la_misma_combinacion_no_se_carga_dos_veces(
    db: AsyncSession, producto: Producto, curva_remeras: CurvaTalle, color_negro: Color
) -> None:
    """La base impide dos veces el mismo producto en el mismo talle y color.

    Sin esa restricción, el stock de esa prenda queda partido en dos filas y
    ninguna de las dos dice cuánto hay.
    """
    from sqlalchemy.exc import IntegrityError

    for sku in ["UNO", "DOS"]:
        db.add(
            Variante(
                producto_id=producto.id,
                talle_id=curva_remeras.talles[0].id,
                color_id=color_negro.id,
                sku=sku,
                activa=True,
            )
        )
    try:
        await db.flush()
    except IntegrityError:
        return
    raise AssertionError("La base aceptó dos variantes iguales")


async def test_el_listado_filtra_por_texto(
    client_admin: AsyncClient, producto: Producto, categoria: Categoria
) -> None:
    """Buscar por parte del nombre encuentra la prenda."""
    assert (
        len((await client_admin.get("/productos", params={"buscar": "lisa"})).json())
        == 1
    )
    assert (
        len((await client_admin.get("/productos", params={"buscar": "campera"})).json())
        == 0
    )


async def test_subir_una_foto(client_admin: AsyncClient, producto: Producto) -> None:
    """Se sube la foto y vuelve la dirección para mostrarla."""
    respuesta = await client_admin.post(
        f"/productos/{producto.id}/imagenes",
        files={"archivo": ("remera.jpg", io.BytesIO(b"contenido"), "image/jpeg")},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["url"].startswith("https://r2.prueba/productos/")


async def test_un_archivo_que_no_es_foto_se_rechaza(
    client_admin: AsyncClient, producto: Producto
) -> None:
    """El mensaje dice qué formatos sirven, no solo que está mal."""
    respuesta = await client_admin.post(
        f"/productos/{producto.id}/imagenes",
        files={"archivo": ("lista.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert respuesta.status_code == 400
    assert "JPG" in respuesta.json()["detail"]


async def test_una_foto_demasiado_pesada_se_rechaza(
    client_admin: AsyncClient, producto: Producto
) -> None:
    """Una foto sin recortar tapa la pantalla del mostrador en conexión lenta."""
    grande = io.BytesIO(b"x" * (3 * 1024 * 1024 + 1))
    respuesta = await client_admin.post(
        f"/productos/{producto.id}/imagenes",
        files={"archivo": ("grande.jpg", grande, "image/jpeg")},
    )
    assert respuesta.status_code == 400
    assert "3 MB" in respuesta.json()["detail"]
