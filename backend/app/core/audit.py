"""
Auditoría automática por fila.

Un único listener de SQLAlchemy sobre `before_flush` hace dos cosas para
cualquier tabla del sistema, sin que ningún service tenga que acordarse:

1. Completa `created_by` / `updated_by` con el usuario de la sesión.
2. Escribe un `AuditLog` por cada alta, cambio o baja, con la diferencia.

Está hecho así, y no llamando a un `registrar_cambio()` desde cada service,
porque lo que depende de que alguien se acuerde algún día no se hace: alcanza
con un endpoint nuevo escrito apurado para que un cambio quede sin rastro, y
lo vas a descubrir el día que necesites saber quién tocó un precio.

Dos detalles del funcionamiento de SQLAlchemy que importan acá:

- La convención "cada tabla tiene id uuid PK con `default=generate_uuid`" hace
  que el id todavía **no** esté asignado durante `before_flush`: SQLAlchemy lo
  calcula recién al armar el INSERT. Se lo asigna este listener, que es
  exactamente lo que haría el default, solo que un poco antes.
- Los `AuditLog` que se agregan acá adentro entran en el mismo flush:
  `before_flush` corre una sola vez, y recién cuando retorna se arma el grafo
  de la unidad de trabajo, así que todo lo agregado acá se procesa junto.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import event, inspect
from sqlalchemy.orm import InstanceState, Session

from app.models.audit_log import AuditLog, OperacionAudit

# Campos que nunca se guardan en claro en el registro de auditoría. El valor ya
# es un hash, pero no hace falta darle más superficie de exposición.
_CAMPOS_REDACTADOS = {"password_hash"}


def _serializar_valor(valor: Any) -> Any:
    """Convierte un valor de columna a algo que entre en un JSON."""
    if isinstance(valor, UUID):
        return str(valor)
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        # Como texto y no como float: el JSON de auditoría de una venta tiene
        # que devolver el importe exacto que se guardó, sin redondeo binario.
        return str(valor)
    if isinstance(valor, Enum):
        return valor.value
    return valor


def _snapshot(obj: Any) -> dict[str, Any]:
    """Foto completa de las columnas del objeto (para altas y bajas)."""
    mapper = inspect(obj).mapper
    snapshot: dict[str, Any] = {}
    for attr in mapper.column_attrs:
        if attr.key in _CAMPOS_REDACTADOS:
            snapshot[attr.key] = "***"
            continue
        snapshot[attr.key] = _serializar_valor(getattr(obj, attr.key))
    return snapshot


def _diff(state: InstanceState[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Solo las columnas que cambiaron, con su valor anterior y el nuevo.

    Límite conocido: si una columna nunca se había leído de la base y se le
    asigna un valor, SQLAlchemy no guarda el anterior en ningún lado — se
    pierde en el momento de la asignación, y ni `load_history()` lo recupera
    después. El registro queda con el valor nuevo y sin el anterior.

    En la práctica no aparece: los endpoints traen la fila con `db.get()`
    antes de tocarla, y eso carga todas las columnas. Solo pasa al modificar
    un objeto recién creado en la misma sesión, y en ese caso la entrada de
    alta —anterior e inmediata— ya tiene la foto completa.
    """
    anteriores: dict[str, Any] = {}
    nuevos: dict[str, Any] = {}
    for attr in state.mapper.column_attrs:
        historial = state.attrs[attr.key].history
        if not historial.has_changes():
            continue
        clave = attr.key
        if clave in _CAMPOS_REDACTADOS:
            if historial.deleted:
                anteriores[clave] = "***"
            if historial.added:
                nuevos[clave] = "***"
            continue
        if historial.deleted:
            anteriores[clave] = _serializar_valor(historial.deleted[0])
        if historial.added:
            nuevos[clave] = _serializar_valor(historial.added[0])
    return anteriores, nuevos


def _registro_id(obj: Any) -> UUID | None:
    """Devuelve el id del objeto, asignándolo si todavía no lo tiene."""
    if getattr(obj, "id", None) is None:
        try:
            obj.id = uuid4()
        except AttributeError:
            return None
    valor = getattr(obj, "id", None)
    return valor if isinstance(valor, UUID) else None


def _sellar_autoria(obj: Any, usuario_id: UUID | None, *, es_alta: bool) -> None:
    """Completa `created_by` / `updated_by` si el modelo los tiene.

    No pisa un `created_by` ya cargado: en una venta sincronizada desde el
    punto de venta offline, quien la registró en el mostrador es el dato que
    vale, no quien disparó la sincronización.
    """
    if usuario_id is None:
        return
    if es_alta and hasattr(obj, "created_by") and obj.created_by is None:
        obj.created_by = usuario_id
    if hasattr(obj, "updated_by"):
        obj.updated_by = usuario_id


@event.listens_for(Session, "before_flush")
def _registrar_auditoria(
    session: Session, _flush_context: Any, _instances: Any
) -> None:
    """Sella la autoría y escribe el registro de auditoría de todo el flush."""
    usuario_id = session.info.get("usuario_id")
    ip_origen = session.info.get("ip_origen")

    for obj in list(session.new):
        if isinstance(obj, AuditLog):
            continue
        registro_id = _registro_id(obj)
        if registro_id is None:
            continue
        _sellar_autoria(obj, usuario_id, es_alta=True)
        session.add(
            AuditLog(
                tabla_afectada=obj.__tablename__,
                registro_id=registro_id,
                operacion=OperacionAudit.create,
                datos_nuevos=_snapshot(obj),
                usuario_id=usuario_id,
                ip_origen=ip_origen,
            )
        )

    for obj in list(session.dirty):
        if isinstance(obj, AuditLog):
            continue
        # El chequeo va antes de sellar `updated_by`: si no, sellarlo dejaría
        # "modificado" a un objeto que en realidad nadie tocó, y cada lectura
        # que pase por un flush escribiría una fila de auditoría vacía.
        if not session.is_modified(obj, include_collections=False):
            continue
        registro_id = _registro_id(obj)
        if registro_id is None:
            continue
        _sellar_autoria(obj, usuario_id, es_alta=False)
        anteriores, nuevos = _diff(inspect(obj))
        if not anteriores and not nuevos:
            continue
        session.add(
            AuditLog(
                tabla_afectada=obj.__tablename__,
                registro_id=registro_id,
                operacion=OperacionAudit.update,
                datos_anteriores=anteriores,
                datos_nuevos=nuevos,
                usuario_id=usuario_id,
                ip_origen=ip_origen,
            )
        )

    for obj in list(session.deleted):
        if isinstance(obj, AuditLog):
            continue
        registro_id = _registro_id(obj)
        if registro_id is None:
            continue
        session.add(
            AuditLog(
                tabla_afectada=obj.__tablename__,
                registro_id=registro_id,
                operacion=OperacionAudit.delete,
                datos_anteriores=_snapshot(obj),
                usuario_id=usuario_id,
                ip_origen=ip_origen,
            )
        )
