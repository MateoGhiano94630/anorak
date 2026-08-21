"""Esquemas de los catálogos: marcas, curvas de talle, talles, colores y categorías."""

import uuid

from pydantic import BaseModel, Field


class MarcaCreate(BaseModel):
    """Alta de marca."""

    nombre: str = Field(min_length=1, max_length=80)


class MarcaUpdate(BaseModel):
    """Modificación de marca."""

    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    activa: bool | None = None


class MarcaOut(BaseModel):
    """Marca como la devuelve la API."""

    id: uuid.UUID
    nombre: str
    activa: bool

    model_config = {"from_attributes": True}


class TalleCreate(BaseModel):
    """Un talle dentro de una curva."""

    valor: str = Field(min_length=1, max_length=10)
    orden: int = 0


class TalleOut(BaseModel):
    """Talle como lo devuelve la API."""

    id: uuid.UUID
    valor: str
    orden: int
    activo: bool

    model_config = {"from_attributes": True}


class CurvaTalleCreate(BaseModel):
    """Alta de una curva con todos sus talles de una vez.

    Se cargan juntos porque una curva sin talles no sirve para nada, y
    dejarla a medias es la forma de que alguien cree una categoría que no
    admite ningún talle.
    """

    nombre: str = Field(min_length=1, max_length=80)
    talles: list[TalleCreate] = Field(min_length=1)


class CurvaTalleUpdate(BaseModel):
    """Modificación de una curva. Los talles se agregan por separado."""

    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    activa: bool | None = None


class CurvaTalleOut(BaseModel):
    """Curva con sus talles, ordenados."""

    id: uuid.UUID
    nombre: str
    activa: bool
    talles: list[TalleOut]

    model_config = {"from_attributes": True}


class ColorCreate(BaseModel):
    """Alta de color."""

    nombre: str = Field(min_length=1, max_length=50)
    codigo_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class ColorUpdate(BaseModel):
    """Modificación de color."""

    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    codigo_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    activo: bool | None = None


class ColorOut(BaseModel):
    """Color como lo devuelve la API."""

    id: uuid.UUID
    nombre: str
    codigo_hex: str | None
    activo: bool

    model_config = {"from_attributes": True}


class CategoriaCreate(BaseModel):
    """Alta de categoría. La curva de talles es obligatoria."""

    nombre: str = Field(min_length=1, max_length=80)
    curva_talle_id: uuid.UUID


class CategoriaUpdate(BaseModel):
    """Modificación de categoría."""

    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    curva_talle_id: uuid.UUID | None = None
    activa: bool | None = None


class CategoriaOut(BaseModel):
    """Categoría como la devuelve la API."""

    id: uuid.UUID
    nombre: str
    curva_talle_id: uuid.UUID
    curva_nombre: str
    activa: bool

    model_config = {"from_attributes": True}
