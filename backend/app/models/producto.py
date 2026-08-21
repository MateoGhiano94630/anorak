"""
Producto, variante e imágenes.

El producto es el molde; la variante es la unidad real. "Remera Nike negra
talle M" es lo que se vende, se cuenta y se repone, y por eso el stock, el
precio y el código de barras cuelgan de la variante y nunca del producto.
Ver D-1 en docs/arquitectura.md.
"""

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUIDType, enum_texto
from app.models.base import AuditMixin, generate_uuid
from app.models.catalogo import Categoria, Color, Marca, Talle


class Genero(StrEnum):
    """Para quién es la prenda."""

    hombre = "HOMBRE"
    mujer = "MUJER"
    unisex = "UNISEX"
    nino = "NINO"
    nina = "NINA"
    bebe = "BEBE"


class Temporada(StrEnum):
    """Temporada a la que pertenece la prenda."""

    verano = "VERANO"
    invierno = "INVIERNO"
    entretiempo = "ENTRETIEMPO"
    atemporal = "ATEMPORAL"


class Producto(Base, AuditMixin):
    """El molde: lo que se nombra en una vidriera, sin talle ni color."""

    __tablename__ = "producto"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("categoria.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    marca_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("marca.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    genero: Mapped[Genero] = mapped_column(
        enum_texto(Genero, 10), nullable=False, default=Genero.unisex
    )
    temporada: Mapped[Temporada] = mapped_column(
        enum_texto(Temporada, 12), nullable=False, default=Temporada.atemporal
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    categoria: Mapped[Categoria] = relationship(lazy="selectin")
    marca: Mapped[Marca | None] = relationship(lazy="selectin")
    variantes: Mapped[list["Variante"]] = relationship(
        back_populates="producto", lazy="selectin"
    )
    imagenes: Mapped[list["ImagenProducto"]] = relationship(
        back_populates="producto", order_by="ImagenProducto.orden", lazy="selectin"
    )

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Producto {self.nombre}>"


class Variante(Base, AuditMixin):
    """
    La unidad real: un producto en un talle y un color concretos.

    Es lo que tiene código de barras, precio y existencias. La restricción de
    unicidad sobre (producto, talle, color) es la que impide cargar dos veces
    la misma prenda y terminar con el stock partido en dos filas.
    """

    __tablename__ = "variante"
    __table_args__ = (
        UniqueConstraint(
            "producto_id",
            "talle_id",
            "color_id",
            name="uq_variante_producto_talle_color",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("producto.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    talle_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("talle.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    color_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("color.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Código interno con el que se busca la prenda en el mostrador. Lo propone
    # el sistema y se puede corregir a mano.
    sku: Mapped[str] = mapped_column(
        String(40), nullable=False, unique=True, index=True
    )
    # El de la etiqueta del proveedor. Opcional: mucha ropa no trae. Único
    # cuando está cargado; varias variantes pueden tenerlo vacío.
    codigo_barras: Mapped[str | None] = mapped_column(
        String(50), nullable=True, unique=True, index=True
    )
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    producto: Mapped[Producto] = relationship(back_populates="variantes")
    talle: Mapped[Talle] = relationship(lazy="selectin")
    color: Mapped[Color] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Variante {self.sku}>"


class ImagenProducto(Base, AuditMixin):
    """
    Una foto del producto, guardada en Cloudflare R2.

    En la base va la clave del objeto y no la URL: las URLs de R2 se firman y
    vencen, así que guardar una dejaría la base llena de direcciones muertas.
    La dirección para mostrar se arma en el momento de servir la respuesta.

    La foto principal es la de `orden` más bajo. No hay un campo "es
    principal" aparte para que no puedan contradecirse.
    """

    __tablename__ = "imagen_producto"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("producto.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clave: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    nombre_original: Mapped[str | None] = mapped_column(String(255), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    producto: Mapped[Producto] = relationship(back_populates="imagenes")

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<ImagenProducto {self.clave}>"
