"""Mixins y helpers comunes a todos los modelos.

Convención del proyecto: toda tabla lleva `id` UUID como clave primaria más
`created_at`, `updated_at`, `created_by` y `updated_by`. Los cuatro campos de
auditoría los completa solo el sistema (ver `app/core/audit.py`); ningún
service tiene que acordarse de escribirlos.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import UUIDType


def generate_uuid() -> uuid.UUID:
    """Genera un UUID v4.

    Los identificadores se generan del lado del cliente y no con un
    autoincremental de la base: el punto de venta tiene que poder registrar
    una venta sin conexión y sincronizarla después. Un id que solo existe una
    vez que el servidor contestó haría imposible ese circuito.
    """
    return uuid.uuid4()


class TimestampMixin:
    """Agrega `created_at` y `updated_at`."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        # CURRENT_TIMESTAMP y no now(): es la forma que entienden los dos
        # motores. `onupdate` es del lado del ORM, así que no cambia.
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        nullable=False,
    )


class AuditMixin(TimestampMixin):
    """Agrega `created_by` y `updated_by` además de los timestamps.

    Quedan nulos cuando la fila la escribe el propio sistema (seed, migración,
    sincronización automática) y no una persona.

    Son UUID sin clave foránea a `usuario`, a diferencia de
    `audit_log.usuario_id`, que sí la tiene. El motivo es un ciclo de claves
    foráneas: estas dos columnas están en *todas* las tablas, así que cualquier
    tabla a la que `usuario` apunte queda apuntándose de vuelta. Con la FK
    puesta, PostgreSQL no puede ordenar la creación de las tablas y la primera
    migración no corre. Ya pasó una vez, con la tabla de sucursales.

    Lo que se pierde es poco: las cuentas se dan de baja de forma lógica y
    nunca se borran, así que un `created_by` apuntando a la nada no puede
    ocurrir.
    """

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
