"""
Los catálogos chicos del sistema: marcas, curvas de talle, talles, colores
y categorías.

Son cerrados a propósito. El dueño eligió catálogo cerrado de talles
(20/08/2026), y la misma razón vale para los colores: si el talle y el color
fueran texto libre, en tres meses conviven "M" con "m" y "Negro" con "negro"
como si fueran cosas distintas. El reporte de qué talles se cambian más —que
es el dato que le dice al local qué está comprando mal— sale partido en dos y
no sirve. El costo es una pantalla de administración por catálogo.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUIDType
from app.models.base import AuditMixin, generate_uuid


class Marca(Base, AuditMixin):
    """Una marca de la mercadería que se vende."""

    __tablename__ = "marca"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    nombre: Mapped[str] = mapped_column(
        String(80), nullable=False, unique=True, index=True
    )
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Marca {self.nombre}>"


class CurvaTalle(Base, AuditMixin):
    """
    Un conjunto de talles que se usan juntos: S-M-L-XL, 36 al 48, 35 al 45.

    Cada categoría apunta a una curva, y las variantes de un producto solo
    pueden usar talles de la curva de su categoría. Es lo que evita cargar una
    remera en talle 42.
    """

    __tablename__ = "curva_talle"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    nombre: Mapped[str] = mapped_column(
        String(80), nullable=False, unique=True, index=True
    )
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    talles: Mapped[list["Talle"]] = relationship(
        back_populates="curva", order_by="Talle.orden", lazy="selectin"
    )

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<CurvaTalle {self.nombre}>"


class Talle(Base, AuditMixin):
    """
    Un talle dentro de una curva.

    `orden` existe porque los talles no se ordenan solos: alfabéticamente, L
    va antes que M y XS antes que XXL, que es al revés de como los busca
    cualquiera. El número lo fija quien carga la curva.
    """

    __tablename__ = "talle"
    __table_args__ = (
        UniqueConstraint("curva_talle_id", "valor", name="uq_talle_curva_valor"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    curva_talle_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("curva_talle.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    valor: Mapped[str] = mapped_column(String(10), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    curva: Mapped[CurvaTalle] = relationship(back_populates="talles")

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Talle {self.valor}>"


class Color(Base, AuditMixin):
    """
    Un color de la mercadería.

    `codigo_hex` es opcional y sirve para mostrar el cuadradito de color en el
    mostrador: buscar "el azul" entre ocho azules escritos es más lento que
    verlos.
    """

    __tablename__ = "color"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    nombre: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    codigo_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Color {self.nombre}>"


class Categoria(Base, AuditMixin):
    """
    El tipo de prenda: remeras, pantalones, calzado, accesorios.

    La curva de talles es obligatoria, incluso para lo que no tiene talle. Un
    cinto o una gorra van en una categoría cuya curva es "Único", con un solo
    talle. Podría haberse permitido que la categoría no tenga curva y que la
    variante quede sin talle, pero eso rompe la restricción de unicidad de las
    variantes: en PostgreSQL dos filas con talle nulo se consideran distintas
    entre sí, así que el mismo producto en el mismo color podría cargarse dos
    veces sin que la base lo impida.
    """

    __tablename__ = "categoria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    nombre: Mapped[str] = mapped_column(
        String(80), nullable=False, unique=True, index=True
    )
    curva_talle_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("curva_talle.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    curva: Mapped[CurvaTalle] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Categoria {self.nombre}>"
