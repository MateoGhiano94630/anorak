"""Lectura del registro de auditoría. Solo para el rol admin."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import AdminUser, DbSession
from app.models.audit_log import AuditLog, OperacionAudit
from app.schemas.audit_log import AuditLogOut

router = APIRouter(prefix="/audit-log", tags=["auditoría"])


@router.get("", response_model=list[AuditLogOut])
async def listar_auditoria(
    db: DbSession,
    _admin: AdminUser,
    tabla: str | None = None,
    registro_id: uuid.UUID | None = None,
    operacion: OperacionAudit | None = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditLog]:
    """Lista los últimos movimientos registrados, del más nuevo al más viejo.

    El registro es de solo lectura: no hay endpoint para modificarlo ni para
    borrarlo, a propósito.
    """
    consulta = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limite)
    if tabla is not None:
        consulta = consulta.where(AuditLog.tabla_afectada == tabla)
    if registro_id is not None:
        consulta = consulta.where(AuditLog.registro_id == registro_id)
    if operacion is not None:
        consulta = consulta.where(AuditLog.operacion == operacion)
    resultado = await db.execute(consulta)
    return list(resultado.scalars().all())
