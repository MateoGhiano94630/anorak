"""
Caja: medios de pago, sesiones y movimientos.

Una **sesión** va desde que alguien abre la caja hasta que la cierra. Es lo
que se arquea, y en este local hay una por jornada: la abre quien llega
primero y cobran todos sobre el mismo cajón.

Un **movimiento** es cada peso que entra o sale. La suma de los movimientos
en efectivo de una sesión abierta es lo que debería haber en el cajón; al
cerrar, esa cuenta se congela y se compara contra lo que se contó.
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


class TipoMedioPago(StrEnum):
    """Con qué se cobra."""

    efectivo = "EFECTIVO"
    tarjeta_debito = "TARJETA_DEBITO"
    tarjeta_credito = "TARJETA_CREDITO"
    qr = "QR"
    transferencia = "TRANSFERENCIA"


class EstadoSesionCaja(StrEnum):
    """En qué estado está una sesión."""

    abierta = "ABIERTA"
    cerrada = "CERRADA"


class TipoMovimientoCaja(StrEnum):
    """Por qué entró o salió la plata.

    `apertura`, `diferencia` y `cierre` los genera el propio circuito de la
    sesión. `cobro` y `devolucion` los va a generar el punto de venta cuando
    exista. `ingreso`, `retiro` y `gasto` los carga una persona.
    """

    apertura = "APERTURA"
    cobro = "COBRO"
    ingreso = "INGRESO"
    retiro = "RETIRO"
    gasto = "GASTO"
    devolucion = "DEVOLUCION"
    diferencia = "DIFERENCIA"
    cierre = "CIERRE"


class TipoDocumentoCaja(StrEnum):
    """Qué clase de documento originó un movimiento."""

    venta = "VENTA"
    devolucion = "DEVOLUCION"
    cambio = "CAMBIO"
    compra = "COMPRA"


class MedioPago(Base, AuditMixin):
    """
    Una forma de cobrar.

    `afecta_efectivo` es lo que separa al efectivo de todo lo demás: es el
    único que entra al cajón y el único que se cuenta en el arqueo. La tarjeta
    y el QR acreditan en una cuenta, días después y con comisión descontada.
    Mezclarlos en el conteo da un arqueo que no cierra nunca.

    La comisión y los días de acreditación no los usa nadie todavía: son lo
    que después va a permitir conciliar contra el resumen del procesador.
    Cargarlos ahora es una columna; agregarlos después es tocar movimientos
    ya cerrados.
    """

    __tablename__ = "medio_pago"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    nombre: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    tipo: Mapped[TipoMedioPago] = mapped_column(
        enum_texto(TipoMedioPago, 20), nullable=False
    )
    # Columna propia y no derivada del tipo: si mañana hay un medio nuevo que
    # no encaja en la lista, quien lo carga decide si entra al cajón sin que
    # haya que tocar código.
    afecta_efectivo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    comision_porcentaje: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    dias_acreditacion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<MedioPago {self.nombre}>"


class SesionCaja(Base, AuditMixin):
    """
    Una jornada de caja: de la apertura al cierre.

    Los tres números del arqueo —lo declarado, lo esperado y la diferencia—
    se congelan al cerrar y no se recalculan nunca. Un arqueo es un documento:
    dice qué se contó y qué creía el sistema **en ese momento**. Si el
    esperado se recalculara, una corrección posterior cambiaría la historia y
    la diferencia dejaría de coincidir con la que la persona vio al cerrar.

    `abierta_por` y `cerrada_por` son columnas propias y no los sellos de
    auditoría: `cerrada_por` no podría salir de ahí, porque cerrar es
    modificar la fila y no crearla.
    """

    __tablename__ = "sesion_caja"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    estado: Mapped[EstadoSesionCaja] = mapped_column(
        enum_texto(EstadoSesionCaja, 10), nullable=False, index=True
    )

    # ── Apertura ─────────────────────────────────────────────────────────────
    fecha_apertura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    abierta_por: Mapped[uuid.UUID] = mapped_column(UUIDType, nullable=False)
    # El fondo con el que arranca el cajón para dar vuelto. No es recaudación.
    monto_inicial: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # ── Cierre y arqueo ──────────────────────────────────────────────────────
    fecha_cierre: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cerrada_por: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    # Lo que se contó a mano.
    efectivo_declarado: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    # Lo que el sistema calculó que debía haber, congelado al cerrar.
    efectivo_esperado: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    # Declarado menos esperado. Negativo es faltante. No se edita nunca.
    diferencia: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    motivo_diferencia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Lo que se sacó del cajón al cerrar y lo que quedó para el día siguiente.
    monto_retirado: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    fondo_dejado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    movimientos: Mapped[list["MovimientoCaja"]] = relationship(
        back_populates="sesion", order_by="MovimientoCaja.numero"
    )

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<SesionCaja {self.estado} {self.fecha_apertura:%d/%m/%Y}>"


class MovimientoCaja(Base, AuditMixin):
    """
    Un peso que entra o sale de la caja. Es un hecho: no se modifica ni se
    borra.

    Corregir un movimiento equivocado se hace con **otro** movimiento, igual
    que en un libro de caja de papel. Editar el original dejaría el sistema
    sin poder contestar qué se creyó que había en cada momento.
    """

    __tablename__ = "movimiento_caja"
    __table_args__ = (
        UniqueConstraint("sesion_id", "numero", name="uq_movimiento_caja_numero"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, primary_key=True, default=generate_uuid
    )
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("sesion_caja.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # El renglón dentro de la sesión: 1, 2, 3. Un libro de caja se lee en
    # orden, y `created_at` no alcanza para darlo: en SQLite tiene precisión
    # de segundos, y en PostgreSQL `CURRENT_TIMESTAMP` devuelve la hora de
    # inicio de la transacción, así que todo lo escrito en la misma
    # transacción queda con el mismo valor. Ordenar por ahí es indeterminado
    # en los dos motores.
    #
    # La restricción de unicidad es la red: si dos personas cargan un
    # movimiento en el mismo instante sobre la misma caja, la segunda falla en
    # vez de quedar con un renglón repetido y un orden inventado.
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[TipoMovimientoCaja] = mapped_column(
        enum_texto(TipoMovimientoCaja, 15), nullable=False, index=True
    )
    medio_pago_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("medio_pago.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Con signo: positivo entra, negativo sale. Sumar la columna de los medios
    # que afectan al efectivo da lo que debería haber en el cajón, y con el
    # signo esa suma es una consulta y no un caso por tipo de movimiento.
    importe: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Obligatorio en lo que carga una persona (ingreso, retiro, gasto): un
    # movimiento de plata sin explicación no lo justifica nadie tres meses
    # después.
    concepto: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Número de factura o recibo del gasto, cuando lo hay.
    comprobante: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # El documento que lo originó. Sin clave foránea a propósito: apunta a
    # tablas distintas según el tipo, y una columna no puede referenciar a
    # varias. Es el gancho por el que va a entrar el cobro de una venta.
    documento_tipo: Mapped[TipoDocumentoCaja | None] = mapped_column(
        enum_texto(TipoDocumentoCaja, 15), nullable=True
    )
    documento_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, nullable=True, index=True
    )

    sesion: Mapped[SesionCaja] = relationship(back_populates="movimientos")
    medio_pago: Mapped[MedioPago] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        """Representación corta para logs y depuración."""
        return f"<MovimientoCaja {self.tipo} {self.importe}>"
