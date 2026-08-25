"""
Ventas y el catálogo opcional de artículos.

Una venta es un **documento histórico**, no una vista de los datos de hoy:
cada línea guarda la descripción y el precio con el que se vendió, copiados y
no traídos por referencia. Si el precio saliera del artículo, el día que suben
los precios cambiarían todas las ventas viejas y los reportes mentirían hacia
atrás.

El catálogo es opcional a propósito. Una línea puede apuntar a un artículo o
ser texto escrito a mano: se puede vender desde el primer día y cargar el
catálogo de a poco, empezando por lo que más se repite. Un módulo de ventas
que exige un catálogo completo antes de la primera venta corre serio riesgo de
no usarse nunca.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUIDType, enum_texto
from app.models.base import AuditMixin, generate_uuid
from app.models.caja import SesionCaja


class EstadoVenta(StrEnum):
    """En qué estado está una venta."""

    registrada = "REGISTRADA"
    anulada = "ANULADA"


class Articulo(Base, AuditMixin):
    """
    Algo que el local vende, con su precio actual.

    Es plano: un artículo por modelo, no uno por talle. "Zapatilla Nike Air"
    es una fila, y el talle se anota en la línea de la venta. Así el catálogo
    de un local que vende de todo son decenas de filas y no cientos, y de
    todos modos se puede contestar qué modelos se venden y en qué talles.

    El precio de acá es solo la **propuesta** para el mostrador. Lo que vale
    para siempre es el que quedó copiado en la línea de la venta.
    """

    __tablename__ = "articulo"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    nombre: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True, index=True
    )
    # Texto libre para agrupar: calzado, remeras, accesorios. Se dejó como
    # texto y no como tabla para que el catálogo siga siendo liviano de
    # cargar. Si con el uso se ensucia —"Remeras" y "remeras" conviviendo—,
    # pasa a ser una tabla; hasta entonces, una tabla más sería ceremonia.
    categoria: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Articulo {self.nombre}>"


class Venta(Base, AuditMixin):
    """
    Una venta del mostrador.

    Pertenece siempre a una sesión de caja: sin caja abierta no se vende, y
    así el arqueo del día cuadra sin excepciones.

    Los cobros **no** son una tabla de esta venta: cada uno es un movimiento
    de caja que apunta acá por `documento_id`. Duplicarlos sería tener dos
    versiones del mismo dato que se pueden desincronizar.
    """

    __tablename__ = "venta"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    # Correlativo propio del sistema. **No** es la numeración fiscal: esa la
    # asigna ARCA al autorizar el comprobante, y hoy está apagado.
    numero: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )
    sesion_caja_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("sesion_caja.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    estado: Mapped[EstadoVenta] = mapped_column(
        enum_texto(EstadoVenta, 12), nullable=False, index=True
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    registrada_por: Mapped[uuid.UUID] = mapped_column(UUIDType, nullable=False)

    # Los tres importes se guardan calculados: una venta es un documento, y
    # recalcular el total al leerlo lo dejaría a merced de cualquier cambio
    # posterior en la forma de calcularlo.
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Anulación ────────────────────────────────────────────────────────────
    anulada_por: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    fecha_anulacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    motivo_anulacion: Mapped[str | None] = mapped_column(String(200), nullable=True)

    sesion_caja: Mapped[SesionCaja] = relationship()
    lineas: Mapped[list["LineaVenta"]] = relationship(
        back_populates="venta", order_by="LineaVenta.numero"
    )

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Venta #{self.numero} {self.total}>"


class LineaVenta(Base, AuditMixin):
    """
    Una prenda vendida, con el precio que tenía en ese momento.

    `descripcion` y `precio_unitario` son copias, no referencias. Aunque la
    línea apunte a un artículo del catálogo, lo que vale para siempre es lo
    que quedó escrito acá: una venta es un documento histórico.
    """

    __tablename__ = "linea_venta"
    __table_args__ = (
        UniqueConstraint("venta_id", "numero", name="uq_linea_venta_numero"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    venta_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("venta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # El renglón dentro de la venta. No sale de `created_at`: ese orden es
    # indeterminado en los dos motores (ver D-14 en docs/arquitectura.md).
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    # Nulo cuando la línea se escribió a mano. Sirve para saber qué se vende;
    # no para saber qué decía la línea, que está en `descripcion`.
    articulo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("articulo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    # El talle vive acá y no en el artículo: así un modelo es una sola fila del
    # catálogo y aun así se puede saber en qué talles se vende.
    talle: Mapped[str | None] = mapped_column(String(15), nullable=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    descuento: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    # cantidad × precio − descuento, guardado.
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    venta: Mapped[Venta] = relationship(back_populates="lineas")
    articulo: Mapped[Articulo | None] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<LineaVenta {self.descripcion} x{self.cantidad}>"
