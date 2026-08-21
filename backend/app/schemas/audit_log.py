"""Esquemas del registro de auditoría."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.audit_log import OperacionAudit


class AuditLogOut(BaseModel):
    """Una entrada del registro de auditoría."""

    id: uuid.UUID
    tabla_afectada: str
    registro_id: uuid.UUID
    operacion: OperacionAudit
    datos_anteriores: dict[str, Any] | None
    datos_nuevos: dict[str, Any] | None
    usuario_id: uuid.UUID | None
    ip_origen: str | None
    ts: datetime

    model_config = {"from_attributes": True}
