"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text  # noqa: F401 — lo usa el repr de JSONB
${imports if imports else ""}

import app.core.types  # noqa: F401 — UUIDType y FlexibleJSON en las columnas

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Aplica la migración."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revierte la migración."""
    ${downgrades if downgrades else "pass"}
