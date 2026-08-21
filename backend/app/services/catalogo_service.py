"""Reglas del catálogo: armado de códigos y generación de variantes."""

import re
import unicodedata
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogo import Categoria, Color, Talle
from app.models.producto import Producto, Variante


def _abreviar(texto: str, largo: int) -> str:
    """Deja las primeras letras y números de un texto, en mayúsculas.

    Saca los acentos antes de recortar: si no, "Niño" y "Nino" generan códigos
    distintos para lo mismo, y el código de barras de una etiqueta impresa no
    coincide con el que el sistema espera.
    """
    sin_acentos = unicodedata.normalize("NFKD", texto)
    solo_ascii = sin_acentos.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]", "", solo_ascii).upper()[:largo]


def _abreviar_nombre(nombre: str, palabras: int = 2, por_palabra: int = 3) -> str:
    """Abrevia el nombre de un producto tomando el arranque de sus palabras.

    "Remera algodón" queda REMALG y "Remera estampada" queda REMEST. Recortar
    el nombre entero a las primeras letras dejaría a los dos como REMER, y un
    local con veinte productos que empiezan con "Remera" terminaría con
    códigos que solo se distinguen por el número que el sistema agrega al
    final: dejan de servir para reconocer la prenda, que es para lo único que
    están.
    """
    partes = [_abreviar(palabra, por_palabra) for palabra in nombre.split()]
    return "".join(parte for parte in partes if parte != "")[: palabras * por_palabra]


async def generar_sku(
    db: AsyncSession, producto: Producto, talle: Talle, color: Color
) -> str:
    """Propone un código interno único para una variante.

    Se arma con marca, producto, talle y color para que sea legible: quien
    atiende lo lee de la etiqueta y sabe qué prenda es sin consultar nada. Si
    ya existe —dos productos de nombre parecido de la misma marca— se le suma
    un número al final hasta que no choque.
    """
    marca = _abreviar(producto.marca.nombre, 3) if producto.marca is not None else "SIN"
    partes = [
        f"{marca}{_abreviar_nombre(producto.nombre)}",
        _abreviar(talle.valor, 4),
        _abreviar(color.nombre, 3),
    ]
    base = "-".join(parte for parte in partes if parte != "")

    candidato = base
    sufijo = 1
    while True:
        existente = await db.execute(select(Variante).where(Variante.sku == candidato))
        if existente.scalar_one_or_none() is None:
            return candidato
        sufijo += 1
        candidato = f"{base}-{sufijo}"


async def talles_validos_de(
    db: AsyncSession, categoria: Categoria
) -> dict[uuid.UUID, Talle]:
    """Devuelve los talles que la categoría admite, por identificador.

    Es lo que impide cargar una remera en talle 42: los talles salen de la
    curva de la categoría y no de una lista suelta.
    """
    resultado = await db.execute(
        select(Talle).where(
            Talle.curva_talle_id == categoria.curva_talle_id, Talle.activo.is_(True)
        )
    )
    return {talle.id: talle for talle in resultado.scalars().all()}


async def generar_variantes(
    db: AsyncSession,
    producto: Producto,
    talle_ids: list[uuid.UUID],
    color_ids: list[uuid.UUID],
) -> list[Variante]:
    """Crea las variantes que faltan para las combinaciones pedidas.

    Es la operación con la que se carga una prenda nueva: se eligen los talles
    y los colores, y salen todas las combinaciones de una vez. Cargarlas de a
    una es lo que hace que alguien se saltee el talle L y no se entere hasta
    que un cliente lo pide.

    Las combinaciones que ya existen se saltean en silencio, así volver a
    ejecutarlo para sumar un color no rompe nada.
    """
    talles = await talles_validos_de(db, producto.categoria)
    faltantes = [str(tid) for tid in talle_ids if tid not in talles]
    if faltantes:
        raise ValueError(
            "Hay talles que no pertenecen a la curva de la categoría del producto"
        )

    resultado = await db.execute(select(Color).where(Color.id.in_(color_ids)))
    colores = {color.id: color for color in resultado.scalars().all()}
    if len(colores) != len(set(color_ids)):
        raise ValueError("Hay colores que no existen")

    existentes = await db.execute(
        select(Variante.talle_id, Variante.color_id).where(
            Variante.producto_id == producto.id
        )
    )
    ya_estan = set(existentes.all())

    nuevas: list[Variante] = []
    for talle_id in talle_ids:
        for color_id in color_ids:
            if (talle_id, color_id) in ya_estan:
                continue
            talle = talles[talle_id]
            color = colores[color_id]
            variante = Variante(
                producto_id=producto.id,
                talle_id=talle_id,
                color_id=color_id,
                sku=await generar_sku(db, producto, talle, color),
                activa=True,
            )
            db.add(variante)
            # El flush va acá adentro y no al final: `generar_sku` consulta si
            # el código ya existe, y sin el flush las variantes de esta misma
            # tanda todavía no están en la base. Dos colores que empiezan
            # igual —"Negro" y "Negro topo"— saldrían con el mismo código.
            await db.flush()
            nuevas.append(variante)
    return nuevas
