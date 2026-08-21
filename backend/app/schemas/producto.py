"""Esquemas de productos y variantes."""

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.producto import Genero, Temporada


class ProductoCreate(BaseModel):
    """Alta de producto. Las variantes se generan aparte."""

    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None
    categoria_id: uuid.UUID
    marca_id: uuid.UUID | None = None
    genero: Genero = Genero.unisex
    temporada: Temporada = Temporada.atemporal


class ProductoUpdate(BaseModel):
    """Modificación de producto."""

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = None
    categoria_id: uuid.UUID | None = None
    marca_id: uuid.UUID | None = None
    genero: Genero | None = None
    temporada: Temporada | None = None
    activo: bool | None = None


class GenerarVariantes(BaseModel):
    """Los talles y colores con los que armar las combinaciones."""

    talle_ids: list[uuid.UUID] = Field(min_length=1)
    color_ids: list[uuid.UUID] = Field(min_length=1)


class VarianteUpdate(BaseModel):
    """Modificación de una variante."""

    sku: str | None = Field(default=None, min_length=1, max_length=40)
    codigo_barras: str | None = Field(default=None, max_length=50)
    activa: bool | None = None


class VarianteOut(BaseModel):
    """Una variante con lo que hace falta para reconocerla en el mostrador."""

    id: uuid.UUID
    producto_id: uuid.UUID
    talle_id: uuid.UUID
    talle: str
    color_id: uuid.UUID
    color: str
    codigo_hex: str | None
    sku: str
    codigo_barras: str | None
    activa: bool
    # Nulo mientras la variante no tenga precio cargado. El punto de venta se
    # niega a venderla en ese caso, en vez de tomarla como si valiera cero.
    precio_venta: Decimal | None
    costo: Decimal | None

    model_config = {"from_attributes": True}


class ImagenOut(BaseModel):
    """Una foto del producto, con la dirección temporal para mostrarla."""

    id: uuid.UUID
    orden: int
    url: str | None


class ProductoOut(BaseModel):
    """Producto como lo devuelve la API, con sus variantes."""

    id: uuid.UUID
    nombre: str
    descripcion: str | None
    categoria_id: uuid.UUID
    categoria: str
    marca_id: uuid.UUID | None
    marca: str | None
    genero: Genero
    temporada: Temporada
    activo: bool
    variantes: list[VarianteOut]
    imagenes: list[ImagenOut]

    model_config = {"from_attributes": True}


class ProductoEnLista(BaseModel):
    """Producto en el listado del catálogo, sin el detalle de cada variante."""

    id: uuid.UUID
    nombre: str
    categoria: str
    marca: str | None
    genero: Genero
    temporada: Temporada
    activo: bool
    cantidad_variantes: int
    # El rango de precios del producto: si todas las variantes valen lo mismo,
    # los dos números coinciden y la pantalla muestra uno solo.
    precio_desde: Decimal | None
    precio_hasta: Decimal | None
    imagen_url: str | None
