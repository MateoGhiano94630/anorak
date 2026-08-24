"""Apertura, movimientos, cierre e historial de la caja."""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import AdminUser, CurrentUser, DbSession, EncargadoUser
from app.models.caja import (
    EstadoSesionCaja,
    MedioPago,
    SesionCaja,
    TipoMovimientoCaja,
)
from app.models.usuario import Usuario
from app.schemas.caja import (
    AperturaCaja,
    CierreCaja,
    MedioPagoCreate,
    MedioPagoOut,
    MedioPagoUpdate,
    MovimientoCajaCreate,
    MovimientoCajaOut,
    SesionCajaOut,
    SesionEnLista,
    TotalPorMedio,
)
from app.services import caja_service

router = APIRouter(prefix="/caja", tags=["caja"])
medios_router = APIRouter(prefix="/medios-pago", tags=["caja"])

# Los tres tipos que carga una persona. El resto los genera el circuito de la
# sesión o, cuando exista, el punto de venta.
_TIPOS_MANUALES = {
    TipoMovimientoCaja.ingreso,
    TipoMovimientoCaja.retiro,
    TipoMovimientoCaja.gasto,
}
# Los que sacan plata del cajón. El importe llega siempre en positivo y el
# signo lo pone el sistema.
_TIPOS_QUE_SACAN = {TipoMovimientoCaja.retiro, TipoMovimientoCaja.gasto}


# ── Medios de pago ────────────────────────────────────────────────────────────


@medios_router.get("", response_model=list[MedioPagoOut])
async def listar_medios(db: DbSession, _usuario: CurrentUser) -> list[MedioPago]:
    """Lista los medios de pago, en el orden en que se muestran al cobrar."""
    resultado = await db.execute(
        select(MedioPago).order_by(MedioPago.orden, MedioPago.nombre)
    )
    return list(resultado.scalars().all())


@medios_router.post(
    "", response_model=MedioPagoOut, status_code=status.HTTP_201_CREATED
)
async def crear_medio(
    datos: MedioPagoCreate, db: DbSession, _admin: AdminUser
) -> MedioPago:
    """Da de alta un medio de pago."""
    medio = MedioPago(
        **{**datos.model_dump(), "nombre": datos.nombre.strip()}, activo=True
    )
    db.add(medio)
    try:
        await db.flush()
    except IntegrityError as err:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un medio de pago con ese nombre"
        ) from err
    return medio


@medios_router.patch("/{medio_id}", response_model=MedioPagoOut)
async def modificar_medio(
    medio_id: uuid.UUID, datos: MedioPagoUpdate, db: DbSession, _admin: AdminUser
) -> MedioPago:
    """Modifica un medio de pago.

    El tipo no se cambia: de él depende si el medio entra al cajón, y
    cambiarlo daría vuelta el sentido de movimientos ya registrados.
    """
    medio = await db.get(MedioPago, medio_id)
    if medio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medio de pago no encontrado")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(medio, campo, valor.strip() if campo == "nombre" else valor)
    try:
        await db.flush()
    except IntegrityError as err:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un medio de pago con ese nombre"
        ) from err
    return medio


# ── Armado de la respuesta ────────────────────────────────────────────────────


async def _nombres_de(db: DbSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Los nombres de los usuarios que abrieron y cerraron, en una consulta."""
    if not ids:
        return {}
    resultado = await db.execute(
        select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids))
    )
    return {fila[0]: fila[1] for fila in resultado.all()}


async def _a_salida(db: DbSession, sesion: SesionCaja) -> SesionCajaOut:
    """Arma la sesión completa, respetando el arqueo a ciegas."""
    abierta = sesion.estado is EstadoSesionCaja.abierta
    nombres = await _nombres_de(
        db, {i for i in (sesion.abierta_por, sesion.cerrada_por) if i is not None}
    )
    totales = await caja_service.totales_por_medio(db, sesion.id)
    medios = {
        medio.id: medio
        for medio in (await db.execute(select(MedioPago))).scalars().all()
    }

    return SesionCajaOut(
        id=sesion.id,
        estado=sesion.estado,
        fecha_apertura=sesion.fecha_apertura,
        abierta_por=sesion.abierta_por,
        abierta_por_nombre=nombres.get(sesion.abierta_por),
        monto_inicial=sesion.monto_inicial,
        fecha_cierre=sesion.fecha_cierre,
        cerrada_por=sesion.cerrada_por,
        cerrada_por_nombre=(
            nombres.get(sesion.cerrada_por) if sesion.cerrada_por else None
        ),
        efectivo_declarado=sesion.efectivo_declarado,
        efectivo_esperado=sesion.efectivo_esperado,
        diferencia=sesion.diferencia,
        motivo_diferencia=sesion.motivo_diferencia,
        monto_retirado=sesion.monto_retirado,
        fondo_dejado=sesion.fondo_dejado,
        observaciones=sesion.observaciones,
        totales_por_medio=[
            TotalPorMedio(
                medio_pago_id=medio_id,
                medio_pago=medios[medio_id].nombre,
                total=total,
            )
            for medio_id, total in totales.items()
            # Mientras la caja está abierta, el efectivo no se informa: es el
            # número que hay que contar, y verlo antes convierte el arqueo en
            # un trámite.
            if not (abierta and medios[medio_id].afecta_efectivo)
        ],
        movimientos=[
            MovimientoCajaOut(
                id=movimiento.id,
                numero=movimiento.numero,
                tipo=movimiento.tipo,
                medio_pago_id=movimiento.medio_pago_id,
                medio_pago=movimiento.medio_pago.nombre,
                importe=movimiento.importe,
                concepto=movimiento.concepto,
                comprobante=movimiento.comprobante,
                documento_tipo=movimiento.documento_tipo,
                documento_id=movimiento.documento_id,
                fecha=movimiento.created_at,
                usuario_id=movimiento.created_by,
            )
            for movimiento in sesion.movimientos
        ],
    )


async def _traer_sesion(db: DbSession, sesion_id: uuid.UUID) -> SesionCaja:
    """Trae la sesión con sus movimientos cargados, o corta con 404.

    `populate_existing` no es decorativo: si la sesión ya se había leído en
    este mismo request, SQLAlchemy devuelve el objeto de su caché **sin**
    volver a cargar la lista de movimientos. La respuesta salía con un
    movimiento menos del que se acababa de registrar.
    """
    resultado = await db.execute(
        select(SesionCaja)
        .options(selectinload(SesionCaja.movimientos))
        .where(SesionCaja.id == sesion_id)
        .execution_options(populate_existing=True)
    )
    sesion = resultado.scalar_one_or_none()
    if sesion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión de caja no encontrada")
    return sesion


async def _abierta_o_error(db: DbSession) -> SesionCaja:
    """La sesión abierta, o un error que explica que hay que abrir la caja."""
    abierta = await caja_service.sesion_abierta(db)
    if abierta is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La caja está cerrada. Abrila antes de registrar movimientos.",
        )
    return await _traer_sesion(db, abierta.id)


# ── Caja ──────────────────────────────────────────────────────────────────────


@router.get("/actual", response_model=SesionCajaOut | None)
async def caja_actual(db: DbSession, _usuario: CurrentUser) -> SesionCajaOut | None:
    """La caja abierta, o nada si está cerrada."""
    abierta = await caja_service.sesion_abierta(db)
    if abierta is None:
        return None
    return await _a_salida(db, await _traer_sesion(db, abierta.id))


@router.get("/fondo-sugerido", response_model=dict[str, str])
async def fondo_sugerido(_usuario: CurrentUser) -> dict[str, str]:
    """El fondo que la apertura propone, para no tipearlo cada mañana."""
    return {"fondo_sugerido": str(settings.fondo_fijo_sugerido)}


@router.post(
    "/apertura", response_model=SesionCajaOut, status_code=status.HTTP_201_CREATED
)
async def abrir_caja(
    datos: AperturaCaja, db: DbSession, usuario: CurrentUser
) -> SesionCajaOut:
    """Abre la caja con el fondo con el que arranca el cajón."""
    try:
        sesion = await caja_service.abrir(
            db, usuario_id=usuario.id, monto_inicial=datos.monto_inicial
        )
    except caja_service.CajaYaAbiertaError as err:
        nombres = await _nombres_de(db, {err.sesion.abierta_por})
        quien = nombres.get(err.sesion.abierta_por, "otra persona")
        cuando = err.sesion.fecha_apertura.strftime("%d/%m/%Y a las %H:%M")
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"La caja ya está abierta. La abrió {quien} el {cuando}.",
        ) from err
    return await _a_salida(db, await _traer_sesion(db, sesion.id))


@router.post(
    "/movimientos",
    response_model=SesionCajaOut,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_movimiento(
    datos: MovimientoCajaCreate, db: DbSession, _usuario: CurrentUser
) -> SesionCajaOut:
    """Registra un ingreso, un retiro o un gasto en efectivo."""
    if datos.tipo not in _TIPOS_MANUALES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Desde acá solo se cargan ingresos, retiros y gastos.",
        )
    sesion = await _abierta_o_error(db)
    efectivo = await caja_service.medio_efectivo(db)
    importe = -datos.importe if datos.tipo in _TIPOS_QUE_SACAN else datos.importe

    try:
        await caja_service.registrar_movimiento(
            db,
            sesion=sesion,
            tipo=datos.tipo,
            importe=importe,
            medio_pago=efectivo,
            concepto=datos.concepto,
            comprobante=datos.comprobante,
        )
    except caja_service.EfectivoInsuficienteError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err

    return await _a_salida(db, await _traer_sesion(db, sesion.id))


@router.post("/cierre", response_model=SesionCajaOut)
async def cerrar_caja(
    datos: CierreCaja, db: DbSession, usuario: CurrentUser
) -> SesionCajaOut:
    """Cierra la caja con el arqueo.

    Es acá donde se revela lo esperado y la diferencia: hasta que no se
    declara lo contado, el sistema no dice cuánto debería haber.
    """
    sesion = await _abierta_o_error(db)
    try:
        await caja_service.cerrar(
            db,
            sesion=sesion,
            usuario_id=usuario.id,
            efectivo_declarado=datos.efectivo_declarado,
            fondo_a_dejar=datos.fondo_a_dejar,
            motivo_diferencia=datos.motivo_diferencia,
            observaciones=datos.observaciones,
        )
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err

    return await _a_salida(db, await _traer_sesion(db, sesion.id))


@router.get("/sesiones", response_model=list[SesionEnLista])
async def listar_sesiones(
    db: DbSession,
    _encargado: EncargadoUser,
    limite: Annotated[int, Query(ge=1, le=200)] = 60,
) -> list[SesionEnLista]:
    """El historial de cajas, de la más nueva a la más vieja.

    Es el reporte que de verdad se usa: no importa que un día falten $500,
    importa si a la misma persona le falta todos los martes.
    """
    resultado = await db.execute(
        select(SesionCaja).order_by(SesionCaja.fecha_apertura.desc()).limit(limite)
    )
    sesiones = list(resultado.scalars().all())
    nombres = await _nombres_de(
        db,
        {s.abierta_por for s in sesiones}
        | {s.cerrada_por for s in sesiones if s.cerrada_por is not None},
    )
    return [
        SesionEnLista(
            id=s.id,
            estado=s.estado,
            fecha_apertura=s.fecha_apertura,
            abierta_por_nombre=nombres.get(s.abierta_por),
            fecha_cierre=s.fecha_cierre,
            cerrada_por_nombre=nombres.get(s.cerrada_por) if s.cerrada_por else None,
            monto_inicial=s.monto_inicial,
            efectivo_declarado=s.efectivo_declarado,
            efectivo_esperado=s.efectivo_esperado,
            diferencia=s.diferencia,
            monto_retirado=s.monto_retirado,
        )
        for s in sesiones
    ]


@router.get("/sesiones/{sesion_id}", response_model=SesionCajaOut)
async def leer_sesion(
    sesion_id: uuid.UUID, db: DbSession, _encargado: EncargadoUser
) -> SesionCajaOut:
    """El detalle de una sesión con su arqueo y sus movimientos."""
    return await _a_salida(db, await _traer_sesion(db, sesion_id))
