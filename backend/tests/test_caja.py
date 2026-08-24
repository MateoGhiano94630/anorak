"""
Caja: apertura, movimientos, arqueo y cierre.

Lo que sostienen estos tests es la regla del módulo: el arqueo es un
documento. Lo declarado, lo esperado y la diferencia se congelan al cerrar y
no se recalculan nunca, y la diferencia no se corrige.
"""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caja import MedioPago, SesionCaja, TipoMovimientoCaja
from app.models.usuario import Usuario
from app.services import caja_service


async def _abrir(cliente: AsyncClient, monto: str = "20000.00") -> dict[str, object]:
    """Abre la caja y devuelve la sesión."""
    respuesta = await cliente.post("/caja/apertura", json={"monto_inicial": monto})
    assert respuesta.status_code == 201, respuesta.text
    cuerpo: dict[str, object] = respuesta.json()
    return cuerpo


# ── Apertura ──────────────────────────────────────────────────────────────────


async def test_sin_caja_abierta_no_hay_nada(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Antes de abrir, la caja del día no existe."""
    respuesta = await client_vendedor.get("/caja/actual")
    assert respuesta.status_code == 200
    assert respuesta.json() is None


async def test_abrir_la_caja(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El vendedor abre con el fondo con el que arranca el cajón."""
    sesion = await _abrir(client_vendedor)
    assert sesion["estado"] == "ABIERTA"
    assert sesion["monto_inicial"] == "20000.00"
    assert sesion["abierta_por_nombre"] == "Vendedor Prueba"


async def test_la_apertura_es_un_movimiento(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El fondo inicial entra como movimiento y no como número aparte.

    Así el efectivo del cajón es siempre la suma de los movimientos, sin
    tener que acordarse de sumarle el inicial por separado.
    """
    sesion = await _abrir(client_vendedor)
    movimientos = sesion["movimientos"]
    assert isinstance(movimientos, list)
    assert len(movimientos) == 1
    assert movimientos[0]["tipo"] == "APERTURA"
    assert movimientos[0]["importe"] == "20000.00"


async def test_no_se_abre_dos_veces(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Y el mensaje dice quién la abrió, para saber a quién buscar."""
    await _abrir(client_vendedor)
    respuesta = await client_vendedor.post(
        "/caja/apertura", json={"monto_inicial": "5000.00"}
    )
    assert respuesta.status_code == 409
    assert "Vendedor Prueba" in respuesta.json()["detail"]


async def test_el_fondo_sugerido_lo_propone_el_sistema(
    client_vendedor: AsyncClient,
) -> None:
    """Para no tipear el mismo número cada mañana."""
    respuesta = await client_vendedor.get("/caja/fondo-sugerido")
    assert respuesta.status_code == 200
    assert Decimal(respuesta.json()["fondo_sugerido"]) > 0


# ── El arqueo es a ciegas ────────────────────────────────────────────────────


async def test_con_la_caja_abierta_no_se_ve_el_efectivo_esperado(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Es la razón de ser del arqueo ciego.

    Si el sistema dijera cuánto debería haber antes de contar, la tentación es
    tipear ese número y el arqueo deja de medir nada.
    """
    sesion = await _abrir(client_vendedor)
    assert sesion["efectivo_esperado"] is None
    assert sesion["diferencia"] is None
    totales = sesion["totales_por_medio"]
    assert isinstance(totales, list)
    assert all(t["medio_pago"] != "Efectivo" for t in totales)


async def test_los_otros_medios_si_se_ven(
    client_vendedor: AsyncClient,
    db: AsyncSession,
    medios_pago: list[MedioPago],
    qr: MedioPago,
) -> None:
    """La tarjeta y el QR no están en el cajón, así que verlos no arruina nada.

    Sirven para cruzar contra el cierre del posnet al final del día.
    """
    await _abrir(client_vendedor)
    sesion_abierta = await caja_service.sesion_abierta(db)
    assert sesion_abierta is not None
    await caja_service.registrar_movimiento(
        db,
        sesion=sesion_abierta,
        tipo=TipoMovimientoCaja.cobro,
        importe=Decimal("15000.00"),
        medio_pago=qr,
    )

    actual = (await client_vendedor.get("/caja/actual")).json()
    totales = {t["medio_pago"]: t["total"] for t in actual["totales_por_medio"]}
    assert totales == {"QR": "15000.00"}


# ── Movimientos ───────────────────────────────────────────────────────────────


async def test_un_ingreso_suma_al_cajon(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Agregar cambio chico se registra: si no, el arqueo da sobrante."""
    await _abrir(client_vendedor)
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "INGRESO", "importe": "5000.00", "concepto": "Cambio chico"},
    )
    assert respuesta.status_code == 201
    movimientos = respuesta.json()["movimientos"]
    assert movimientos[-1]["importe"] == "5000.00"


async def test_un_retiro_resta_del_cajon(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El importe se carga en positivo y el sistema le pone el signo.

    Pedirle a quien atiende que escriba un número negativo para sacar plata es
    una forma de que un día cargue el signo al revés.
    """
    await _abrir(client_vendedor)
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "RETIRO", "importe": "8000.00", "concepto": "Al cofre"},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["movimientos"][-1]["importe"] == "-8000.00"


async def test_un_gasto_guarda_su_comprobante(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Pagarle al flete de la caja sale del cajón y no es una venta."""
    await _abrir(client_vendedor)
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={
            "tipo": "GASTO",
            "importe": "3500.00",
            "concepto": "Flete del proveedor",
            "comprobante": "0001-00012345",
        },
    )
    assert respuesta.status_code == 201
    ultimo = respuesta.json()["movimientos"][-1]
    assert ultimo["importe"] == "-3500.00"
    assert ultimo["comprobante"] == "0001-00012345"


async def test_no_se_puede_sacar_mas_de_lo_que_hay(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Es una acción que está por pasar, así que se frena antes."""
    await _abrir(client_vendedor, "10000.00")
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "RETIRO", "importe": "15000.00", "concepto": "Al cofre"},
    )
    assert respuesta.status_code == 400


async def test_el_error_de_retiro_no_revela_cuanto_hay(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El mensaje de error no puede ser la forma de espiar el saldo.

    Con el arqueo a ciegas, un "quedan $10.000" en el error haría inútil todo
    lo demás.
    """
    await _abrir(client_vendedor, "10000.00")
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "RETIRO", "importe": "15000.00", "concepto": "Al cofre"},
    )
    assert "10000" not in respuesta.json()["detail"]
    assert "10.000" not in respuesta.json()["detail"]


async def test_el_retiro_rechazado_no_deja_movimiento(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Un movimiento rechazado no puede haber tocado el cajón."""
    await _abrir(client_vendedor, "10000.00")
    await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "RETIRO", "importe": "15000.00", "concepto": "Al cofre"},
    )
    actual = (await client_vendedor.get("/caja/actual")).json()
    assert len(actual["movimientos"]) == 1


async def test_el_movimiento_a_mano_necesita_motivo(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Un movimiento de plata sin explicación no lo justifica nadie después."""
    await _abrir(client_vendedor)
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "RETIRO", "importe": "1000.00", "concepto": ""},
    )
    assert respuesta.status_code == 422


async def test_no_se_registra_nada_con_la_caja_cerrada(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Y el mensaje dice qué hacer, no solo que no se puede."""
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "INGRESO", "importe": "1000.00", "concepto": "Cambio"},
    )
    assert respuesta.status_code == 409
    assert "Abrila" in respuesta.json()["detail"]


async def test_desde_la_pantalla_no_se_cargan_cobros(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Los cobros los va a generar el punto de venta, no una carga a mano."""
    await _abrir(client_vendedor)
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "COBRO", "importe": "1000.00", "concepto": "Una venta"},
    )
    assert respuesta.status_code == 400


async def test_el_movimiento_registra_quien_lo_hizo(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El "quién" sale de la auditoría automática, sin que el service lo escriba."""
    await _abrir(client_vendedor)
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "GASTO", "importe": "500.00", "concepto": "Café"},
    )
    assert respuesta.json()["movimientos"][-1]["usuario_id"] is not None


# ── Cierre y arqueo ───────────────────────────────────────────────────────────


async def test_cerrar_con_el_arqueo_justo(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Cuando lo contado coincide, no hay que explicar nada."""
    await _abrir(client_vendedor, "20000.00")
    respuesta = await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "20000.00", "fondo_a_dejar": "20000.00"},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "CERRADA"
    assert cuerpo["diferencia"] == "0.00"
    assert cuerpo["efectivo_esperado"] == "20000.00"


async def test_al_cerrar_se_revela_lo_esperado(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Recién después de declarar lo contado, el sistema dice cuánto había."""
    await _abrir(client_vendedor, "20000.00")
    await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "INGRESO", "importe": "5000.00", "concepto": "Cambio"},
    )
    cierre = await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "25000.00", "fondo_a_dejar": "20000.00"},
    )
    assert cierre.json()["efectivo_esperado"] == "25000.00"


async def test_un_faltante_obliga_a_explicarlo(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """La explicación se pide el día que pasó, que es cuando se acuerdan."""
    await _abrir(client_vendedor, "20000.00")
    respuesta = await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "19500.00", "fondo_a_dejar": "19500.00"},
    )
    assert respuesta.status_code == 400
    assert "diferencia" in respuesta.json()["detail"]


async def test_un_faltante_con_motivo_cierra(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """La diferencia se registra, no se corrige."""
    await _abrir(client_vendedor, "20000.00")
    respuesta = await client_vendedor.post(
        "/caja/cierre",
        json={
            "efectivo_declarado": "19500.00",
            "fondo_a_dejar": "19500.00",
            "motivo_diferencia": "Vuelto mal dado a la mañana",
        },
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["diferencia"] == "-500.00"
    assert cuerpo["efectivo_declarado"] == "19500.00"
    assert cuerpo["efectivo_esperado"] == "20000.00"
    assert cuerpo["motivo_diferencia"] == "Vuelto mal dado a la mañana"


async def test_un_sobrante_tambien_es_una_diferencia(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Que sobre plata no es una buena noticia: es un cobro que no se registró."""
    await _abrir(client_vendedor, "20000.00")
    respuesta = await client_vendedor.post(
        "/caja/cierre",
        json={
            "efectivo_declarado": "20300.00",
            "fondo_a_dejar": "20000.00",
            "motivo_diferencia": "Apareció de más",
        },
    )
    assert respuesta.json()["diferencia"] == "300.00"


async def test_el_cierre_retira_lo_que_sobra_del_fondo(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El cajón arranca cada día con el mismo fondo para vuelto."""
    await _abrir(client_vendedor, "20000.00")
    await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "INGRESO", "importe": "45000.00", "concepto": "Cobros del día"},
    )
    respuesta = await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "65000.00", "fondo_a_dejar": "20000.00"},
    )
    cuerpo = respuesta.json()
    assert cuerpo["monto_retirado"] == "45000.00"
    assert cuerpo["fondo_dejado"] == "20000.00"
    assert cuerpo["movimientos"][-1]["tipo"] == "CIERRE"
    assert cuerpo["movimientos"][-1]["importe"] == "-45000.00"


async def test_despues_de_cerrar_el_libro_cuadra_con_el_cajon(
    client_vendedor: AsyncClient, db: AsyncSession, medios_pago: list[MedioPago]
) -> None:
    """La suma de los movimientos tiene que dar el fondo que quedó.

    Es el invariante del cierre. Por eso la diferencia se anota **como
    movimiento**: un faltante que no se anota deja el libro diciendo una cosa
    y el cajón otra.
    """
    sesion = await _abrir(client_vendedor, "20000.00")
    await client_vendedor.post(
        "/caja/cierre",
        json={
            "efectivo_declarado": "19500.00",
            "fondo_a_dejar": "15000.00",
            "motivo_diferencia": "Faltaron 500",
        },
    )
    en_caja = await caja_service.efectivo_en_caja(db, sesion["id"])  # type: ignore[arg-type]
    assert en_caja == Decimal("15000.00")


async def test_los_numeros_del_arqueo_quedan_congelados(
    client_vendedor: AsyncClient, db: AsyncSession, medios_pago: list[MedioPago]
) -> None:
    """El esperado guardado no se recalcula nunca.

    Después del cierre, la suma de los movimientos ya no da el esperado
    —porque el propio cierre agregó la diferencia y el retiro—, y sin embargo
    el arqueo sigue diciendo lo que decía cuando la persona lo firmó.
    """
    sesion = await _abrir(client_vendedor, "20000.00")
    cierre = await client_vendedor.post(
        "/caja/cierre",
        json={
            "efectivo_declarado": "19500.00",
            "fondo_a_dejar": "15000.00",
            "motivo_diferencia": "Faltaron 500",
        },
    )
    guardado = await db.get(SesionCaja, sesion["id"])
    assert guardado is not None
    assert guardado.efectivo_esperado == Decimal("20000.00")
    assert cierre.json()["efectivo_esperado"] == "20000.00"

    en_caja = await caja_service.efectivo_en_caja(db, sesion["id"])  # type: ignore[arg-type]
    assert en_caja != guardado.efectivo_esperado


async def test_no_se_puede_dejar_mas_de_lo_que_hay(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El fondo que queda sale del efectivo contado, no del esperado."""
    await _abrir(client_vendedor, "10000.00")
    respuesta = await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "10000.00", "fondo_a_dejar": "15000.00"},
    )
    assert respuesta.status_code == 400


async def test_no_se_cierra_dos_veces(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El cierre es definitivo."""
    await _abrir(client_vendedor, "10000.00")
    await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "10000.00", "fondo_a_dejar": "10000.00"},
    )
    respuesta = await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "10000.00", "fondo_a_dejar": "10000.00"},
    )
    assert respuesta.status_code == 409


async def test_despues_de_cerrar_se_puede_abrir_de_nuevo(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El turno siguiente arranca con su propia sesión."""
    await _abrir(client_vendedor, "10000.00")
    await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "10000.00", "fondo_a_dejar": "10000.00"},
    )
    assert (await client_vendedor.get("/caja/actual")).json() is None
    sesion = await _abrir(client_vendedor, "10000.00")
    assert sesion["estado"] == "ABIERTA"


# ── Historial y permisos ──────────────────────────────────────────────────────


async def test_el_vendedor_no_ve_el_historial(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Los cierres los revisa el encargado."""
    assert (await client_vendedor.get("/caja/sesiones")).status_code == 403


async def test_el_encargado_ve_el_historial_con_las_diferencias(
    client_encargado: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """Es el reporte que de verdad se usa."""
    await _abrir(client_encargado, "20000.00")
    await client_encargado.post(
        "/caja/cierre",
        json={
            "efectivo_declarado": "19800.00",
            "fondo_a_dejar": "19800.00",
            "motivo_diferencia": "Faltaron 200",
        },
    )
    respuesta = await client_encargado.get("/caja/sesiones")
    assert respuesta.status_code == 200
    fila = respuesta.json()[0]
    assert fila["diferencia"] == "-200.00"
    assert fila["cerrada_por_nombre"] == "Encargado Prueba"


async def test_los_medios_de_pago_los_administra_el_admin(
    client_encargado: AsyncClient, client_admin: AsyncClient
) -> None:
    """Cualquiera los lee para cobrar; darlos de alta es del administrador."""
    assert (await client_encargado.get("/medios-pago")).status_code == 200
    respuesta = await client_encargado.post(
        "/medios-pago", json={"nombre": "Cheque", "tipo": "TRANSFERENCIA"}
    )
    assert respuesta.status_code == 403
    assert (
        await client_admin.post(
            "/medios-pago",
            json={
                "nombre": "Cheque",
                "tipo": "TRANSFERENCIA",
                "dias_acreditacion": 30,
            },
        )
    ).status_code == 201


async def test_los_importes_viajan_como_texto(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """ "20000.50" y no el número 20000.5.

    Los decimales de JavaScript no representan exactamente los centavos, y esa
    diferencia aparece sumada en un cierre de caja.
    """
    sesion = await _abrir(client_vendedor, "20000.50")
    assert sesion["monto_inicial"] == "20000.50"


async def test_sin_efectivo_cargado_la_caja_no_abre(
    db: AsyncSession, usuario_vendedor: Usuario
) -> None:
    """La apertura es un movimiento, y todo movimiento tiene un medio.

    Sin un medio en efectivo cargado, la caja no puede abrirse, y el mensaje
    lo dice en vez de fallar con un error de base de datos.
    """
    with pytest.raises(RuntimeError, match="efectivo"):
        await caja_service.abrir(
            db, usuario_id=usuario_vendedor.id, monto_inicial=Decimal("100.00")
        )


async def test_los_movimientos_llevan_su_numero_de_renglon(
    client_vendedor: AsyncClient, medios_pago: list[MedioPago]
) -> None:
    """El libro se lee en orden, y ese orden no puede salir de la hora.

    En SQLite `CURRENT_TIMESTAMP` tiene precisión de segundos, y en PostgreSQL
    devuelve la hora de inicio de la transacción: todo lo escrito en el mismo
    flush queda con el mismo valor. Ordenar por ahí es indeterminado.
    """
    await _abrir(client_vendedor, "20000.00")
    await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "INGRESO", "importe": "1000.00", "concepto": "Cambio"},
    )
    respuesta = await client_vendedor.post(
        "/caja/movimientos",
        json={"tipo": "GASTO", "importe": "500.00", "concepto": "Café"},
    )
    movimientos = respuesta.json()["movimientos"]
    assert [m["numero"] for m in movimientos] == [1, 2, 3]
    assert [m["tipo"] for m in movimientos] == ["APERTURA", "INGRESO", "GASTO"]
