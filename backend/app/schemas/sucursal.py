"""Esquemas de sucursales."""

import uuid

from pydantic import BaseModel, Field

from app.models.sucursal import TipoSucursal


class SucursalBase(BaseModel):
    """Campos que se cargan desde la pantalla de sucursales."""

    nombre: str = Field(min_length=1, max_length=100)
    codigo: str = Field(min_length=1, max_length=10)
    tipo: TipoSucursal = TipoSucursal.local
    direccion: str | None = Field(default=None, max_length=200)
    localidad: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=30)
    punto_venta_arca: int | None = None


class SucursalCreate(SucursalBase):
    """Alta de sucursal."""


class SucursalUpdate(BaseModel):
    """Modificación de sucursal. Todo opcional: se manda solo lo que cambia."""

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    tipo: TipoSucursal | None = None
    direccion: str | None = Field(default=None, max_length=200)
    localidad: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=30)
    punto_venta_arca: int | None = None
    activa: bool | None = None


class SucursalOut(SucursalBase):
    """Sucursal como la devuelve la API."""

    id: uuid.UUID
    activa: bool

    model_config = {"from_attributes": True}
