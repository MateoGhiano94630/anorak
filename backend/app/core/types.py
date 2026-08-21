"""
Tipos de columna que funcionan igual en PostgreSQL y en SQLite.

Los tests corren sobre SQLite en memoria (sin .env, sin red, sin Docker) y
producción corre sobre PostgreSQL. Para que un mismo modelo sirva en las dos
bases, ningún modelo puede usar tipos del dialecto `postgresql` directamente:
`UUID(as_uuid=True)` y `JSONB` explotan al crear las tablas en SQLite.
"""

import enum
import uuid

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import TypeDecorator


class UUIDType(TypeDecorator[uuid.UUID]):
    """
    UUID portable: tipo nativo en PostgreSQL, String(36) en SQLite.

    Nunca usar `UUID(as_uuid=True)` de `sqlalchemy.dialects.postgresql` en un
    modelo: rompe la creación de tablas en SQLite y con eso toda la suite.
    """

    impl = String(36)
    cache_ok = True

    def process_bind_param(
        self, value: uuid.UUID | str | None, dialect: Dialect
    ) -> str | None:
        """Convierte el valor de Python a lo que se guarda en la base."""
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> uuid.UUID | None:
        """Convierte lo leído de la base a un UUID de Python."""
        if value is None:
            return None
        return uuid.UUID(str(value))

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[object]:
        """Elige el tipo real según el motor de la conexión."""
        from sqlalchemy.dialects.postgresql import UUID as PGUUID

        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))  # type: ignore[arg-type]
        return dialect.type_descriptor(String(36))  # type: ignore[arg-type]


# JSON portable: JSONB en PostgreSQL (indexable, tipado), JSON en SQLite.
# Mismo motivo que UUIDType: JSONB a secas no existe en SQLite.
FlexibleJSON = JSONB().with_variant(SQLITE_JSON(), "sqlite")


def enum_texto(enum_class: type[enum.StrEnum], largo: int = 30) -> Enum:
    """Columna de texto que guarda un StrEnum y lo devuelve como el enum.

    Tres decisiones metidas en una función para no repetirlas —ni olvidarse de
    alguna— en cada columna:

    - `native_enum=False`: se guarda como texto y no como el tipo ENUM de
      PostgreSQL. Sumar un estado nuevo no obliga a migrar un tipo de la base,
      y de paso funciona igual en SQLite, que es donde corren los tests.
    - `create_constraint=False`: tampoco se genera el CHECK con la lista de
      valores, que traería el mismo problema por la puerta de atrás.
    - `values_callable`: SQLAlchemy guarda por defecto el *nombre* del miembro
      (`admin`) y no su valor (`ADMIN`). Sin esto, lo que queda escrito en la
      base no es lo mismo que viaja por la API.

    Usar `String` pelado y anotar `Mapped[MiEnum]` parece equivalente y no lo
    es: la fila leída de la base vuelve como `str`, y cualquier código que
    haga `.value` sobre ella explota recién en producción.
    """
    return Enum(
        enum_class,
        native_enum=False,
        create_constraint=False,
        length=largo,
        values_callable=lambda miembros: [miembro.value for miembro in miembros],
    )
