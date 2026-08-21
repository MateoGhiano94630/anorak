"""
Historial de precios por variante.

En un local de ropa el margen es el negocio, y sin historial no se puede
explicar por qué cayó — que es justo la pregunta que aparece cuando cae
(D-7 en docs/arquitectura.md).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUIDType
from app.models.base import AuditMixin, generate_uuid
from app.models.producto import Variante


class Precio(Base, AuditMixin):
    """
    Lo que costó y a cuánto se vendió una variante durante un período.

    El precio vigente es la fila con `vigente_hasta` nulo. Cuando cambia, se
    le pone fecha de fin a la anterior y se agrega una nueva: las filas viejas
    no se tocan nunca.

    Por qué no se guarda además el precio actual como columna de `variante`
    —que es lo que sí se va a hacer con el stock—: son dos formas distintas de
    dato. El stock es una suma de movimientos, una cuenta que puede
    desviarse, y por eso conviene tener el total guardado y poder compararlo
    contra la suma. El precio no es una cuenta: es un estado, y en cualquier
    momento hay exactamente una fila vigente. Copiarlo a `variante` solo
    agregaría una segunda versión del mismo dato que se puede desincronizar,
    sin ganar la posibilidad de detectar nada.

    El índice único parcial es el que garantiza ese "exactamente una": la base
    no deja que existan dos precios vigentes para la misma variante, aunque
    haya un error en el código que los escribe.
    """

    __tablename__ = "precio"
    __table_args__ = (
        Index(
            "uq_precio_vigente_por_variante",
            "variante_id",
            unique=True,
            postgresql_where=text("vigente_hasta IS NULL"),
            sqlite_where=text("vigente_hasta IS NULL"),
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
    # Toda la plata en Numeric. Jamás float: un centavo mal redondeado en un
    # cierre de caja es una hora de alguien buscándolo.
    costo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Queda modelado aunque hoy el local no venda por mayor (respuesta del
    # dueño, 20/08/2026). Es una columna sin usar, y eso es más barato que
    # abrir después el historial a varias listas de precios.
    precio_mayorista: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    vigente_desde: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    vigente_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Por qué cambió: "lista nueva del proveedor", "liquidación de temporada".
    # Sin el motivo, el historial dice cuándo cambió pero no por qué, que es
    # la mitad interesante.
    motivo: Mapped[str | None] = mapped_column(String(200), nullable=True)

    variante: Mapped[Variante] = relationship()

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<Precio {self.precio_venta} desde {self.vigente_desde}>"
