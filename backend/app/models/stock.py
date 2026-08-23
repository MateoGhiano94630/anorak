"""
Existencias por variante y sucursal, y los movimientos que las explican.

Dos tablas que dicen lo mismo de dos formas distintas, a propósito:

- `stock` guarda cuánto hay ahora. Es lo que se consulta mil veces por día.
- `movimiento_stock` guarda cada variación como un hecho que no se borra. La
  suma de los movimientos de una variante en una sucursal tiene que dar el
  número de `stock`.

Que existan las dos es la decisión (D-3 en docs/arquitectura.md): **si los dos
números no coinciden, hay un bug y tiene que notarse**. Un sistema que solo
guarda el saldo no puede darse cuenta de que se corrompió, y en un local eso
se descubre contando la mercadería a mano.
"""

import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUIDType, enum_texto
from app.models.base import AuditMixin, generate_uuid
from app.models.producto import Variante
from app.models.sucursal import Sucursal


class TipoMovimiento(StrEnum):
    """Por qué cambió la cantidad.

    `ingreso` y `ajuste` los genera una persona desde la pantalla de
    existencias. El resto los genera el módulo que corresponde: la venta, la
    devolución, la transferencia o el conteo. Están declarados desde ahora
    porque el tipo se guarda como texto: sumar un valor no obliga a migrar
    nada, pero tener la lista completa a la vista evita que cada módulo
    invente su propio nombre para lo mismo.
    """

    ingreso = "INGRESO"
    ajuste = "AJUSTE"
    venta = "VENTA"
    devolucion = "DEVOLUCION"
    transferencia_salida = "TRANSFERENCIA_SALIDA"
    transferencia_entrada = "TRANSFERENCIA_ENTRADA"
    conteo = "CONTEO"


class TipoDocumento(StrEnum):
    """Qué clase de documento originó un movimiento."""

    venta = "VENTA"
    devolucion = "DEVOLUCION"
    cambio = "CAMBIO"
    transferencia = "TRANSFERENCIA"
    compra = "COMPRA"
    conteo = "CONTEO"


class Stock(Base, AuditMixin):
    """Cuántas unidades de una variante hay en una sucursal, ahora."""

    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint(
            "variante_id", "sucursal_id", name="uq_stock_variante_sucursal"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    variante_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("variante.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sucursal_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("sucursal.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Unidades enteras: no se vende media remera. Es lo único del sistema que
    # cuenta cosas en vez de plata, y por eso no es Numeric.
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Debajo de este número, la prenda aparece en las alertas. Cero significa
    # que no se controla.
    stock_minimo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    variante: Mapped[Variante] = relationship(lazy="selectin")
    sucursal: Mapped[Sucursal] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Stock {self.variante_id} en {self.sucursal_id}: {self.cantidad}>"


class MovimientoStock(Base, AuditMixin):
    """
    Una variación de existencias. Es un hecho: no se modifica ni se borra.

    Corregir un movimiento equivocado se hace con **otro** movimiento, igual
    que en un libro contable. Editar el original dejaría el sistema sin poder
    contestar qué se creyó que había en cada momento, que es la mitad de para
    qué sirve tener movimientos.
    """

    __tablename__ = "movimiento_stock"
    __table_args__ = (
        # La consulta que se hace siempre: qué le pasó a esta prenda en este
        # local, en orden. Sin este índice, reconstruir el stock de una
        # variante recorre la tabla entera.
        Index("ix_movimiento_variante_sucursal", "variante_id", "sucursal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    variante_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("variante.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sucursal_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("sucursal.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[TipoMovimiento] = mapped_column(
        enum_texto(TipoMovimiento, 25), nullable=False, index=True
    )
    # Con signo: positivo entra, negativo sale. Sumar la columna de una
    # variante en una sucursal tiene que dar su cantidad actual, y con el signo
    # esa suma es una sola consulta en vez de un caso por tipo de movimiento.
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    # Cuánto quedó justo después de este movimiento. Es una foto histórica, no
    # una copia del saldo: permite contestar cuánto había en una fecha sin
    # sumar todo de nuevo, y sobre todo permite encontrar **en qué movimiento**
    # se rompió la cadena si algún día el saldo y la suma dejan de coincidir.
    cantidad_resultante: Mapped[int] = mapped_column(Integer, nullable=False)
    # Por qué se movió. Obligatorio en los ajustes que carga una persona: un
    # ajuste sin motivo es un número que nadie va a poder explicar después.
    motivo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # El documento que lo originó, cuando hay uno. Sin clave foránea a
    # propósito: apunta a tablas distintas según el tipo, y una columna no
    # puede referenciar a cinco tablas. La integridad la sostiene el módulo
    # que crea el movimiento.
    documento_tipo: Mapped[TipoDocumento | None] = mapped_column(
        enum_texto(TipoDocumento, 15), nullable=True
    )
    documento_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, nullable=True, index=True
    )

    variante: Mapped[Variante] = relationship(lazy="selectin")
    sucursal: Mapped[Sucursal] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<MovimientoStock {self.tipo} {self.cantidad:+d}>"
