"""
Ventas del mostrador.

Lo que sostienen estos tests son dos reglas: una venta es un documento
histórico —guarda el precio con el que se vendió, no una referencia—, y toda
venta cobrada tiene que aparecer en el arqueo de una caja.
"""

from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caja import MedioPago
from app.models.venta import Articulo, Venta
from app.services import caja_service


async def _abrir_caja(cliente: AsyncClient, monto: str = "20000.00") -> None:
    """Abre la caja: sin caja abierta no se vende."""
    respuesta = await cliente.post("/caja/apertura", json={"monto_inicial": monto})
    assert respuesta.status_code == 201, respuesta.text


def _venta(
    efectivo: MedioPago, importe: str, descripcion: str = "Campera azul"
) -> dict[str, object]:
    """Una venta de una línea escrita a mano, pagada toda en efectivo."""
    return {
        "lineas": [
            {"descripcion": descripcion, "cantidad": 1, "precio_unitario": importe}
        ],
        "pagos": [{"medio_pago_id": str(efectivo.id), "importe": importe}],
    }


# ── Registrar una venta ───────────────────────────────────────────────────────


async def test_no_se_vende_con_la_caja_cerrada(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Toda venta pertenece a una sesión de caja, así el arqueo cuadra siempre."""
    respuesta = await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))
    assert respuesta.status_code == 409
    assert "Abrila" in respuesta.json()["detail"]


async def test_una_venta_con_linea_escrita_a_mano(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Se puede vender sin catálogo desde el primer día."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas", json=_venta(efectivo, "50000.00", "Gorra negra")
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["numero"] == 1
    assert cuerpo["total"] == "50000.00"
    assert cuerpo["lineas"][0]["descripcion"] == "Gorra negra"
    assert cuerpo["lineas"][0]["articulo_id"] is None


async def test_una_venta_desde_el_catalogo(
    client_vendedor: AsyncClient, efectivo: MedioPago, articulo: Articulo
) -> None:
    """La descripción se copia del artículo, y el talle va en la línea."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {
                    "articulo_id": str(articulo.id),
                    "talle": "42",
                    "cantidad": 1,
                    "precio_unitario": "185000.00",
                }
            ],
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "185000.00"}],
        },
    )
    assert respuesta.status_code == 201
    linea = respuesta.json()["lineas"][0]
    assert linea["descripcion"] == "Zapatilla Nike Air"
    assert linea["talle"] == "42"
    assert linea["articulo_id"] == str(articulo.id)


async def test_la_venta_guarda_el_precio_con_el_que_se_vendio(
    client_vendedor: AsyncClient,
    client_admin: AsyncClient,
    db: AsyncSession,
    efectivo: MedioPago,
    articulo: Articulo,
) -> None:
    """Subir el precio del catálogo no toca las ventas viejas.

    Si el precio saliera por referencia al artículo, el día que suben los
    precios cambiarían todas las ventas anteriores y los reportes de
    rentabilidad mentirían hacia atrás.
    """
    await _abrir_caja(client_vendedor)
    venta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {
                    "articulo_id": str(articulo.id),
                    "cantidad": 1,
                    "precio_unitario": "185000.00",
                }
            ],
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "185000.00"}],
        },
    )
    venta_id = venta.json()["id"]

    await client_admin.patch(f"/articulos/{articulo.id}", json={"precio": "220000.00"})

    releida = (await client_vendedor.get(f"/ventas/{venta_id}")).json()
    assert releida["lineas"][0]["precio_unitario"] == "185000.00"
    assert releida["total"] == "185000.00"


async def test_una_venta_con_varias_lineas_y_cantidades(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """El subtotal de cada línea es cantidad por precio."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {
                    "descripcion": "Remera lisa",
                    "cantidad": 3,
                    "precio_unitario": "25000.00",
                },
                {
                    "descripcion": "Bermuda",
                    "cantidad": 1,
                    "precio_unitario": "40000.00",
                },
            ],
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "115000.00"}],
        },
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["lineas"][0]["subtotal"] == "75000.00"
    assert cuerpo["total"] == "115000.00"


async def test_las_lineas_llevan_su_numero_de_renglon(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """El orden de las líneas no puede salir de la hora de creación."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {"descripcion": "Primero", "cantidad": 1, "precio_unitario": "1000.00"},
                {"descripcion": "Segundo", "cantidad": 1, "precio_unitario": "2000.00"},
                {"descripcion": "Tercero", "cantidad": 1, "precio_unitario": "3000.00"},
            ],
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "6000.00"}],
        },
    )
    lineas = respuesta.json()["lineas"]
    assert [linea["numero"] for linea in lineas] == [1, 2, 3]
    assert [linea["descripcion"] for linea in lineas] == [
        "Primero",
        "Segundo",
        "Tercero",
    ]


async def test_los_numeros_de_venta_son_correlativos(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Para poder buscar una venta por su número."""
    await _abrir_caja(client_vendedor)
    for esperado in (1, 2, 3):
        respuesta = await client_vendedor.post(
            "/ventas", json=_venta(efectivo, "1000.00")
        )
        assert respuesta.json()["numero"] == esperado


# ── Descuentos ────────────────────────────────────────────────────────────────


async def test_descuento_en_una_linea(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Se puede bajar el precio de una prenda puntual."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {
                    "descripcion": "Campera",
                    "cantidad": 1,
                    "precio_unitario": "100000.00",
                    "descuento": "15000.00",
                }
            ],
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "85000.00"}],
        },
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["lineas"][0]["subtotal"] == "85000.00"


async def test_descuento_sobre_el_total(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Y además se puede hacer un descuento al pie de la venta."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {"descripcion": "Remera", "cantidad": 2, "precio_unitario": "25000.00"}
            ],
            "descuento": "5000.00",
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "45000.00"}],
        },
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["subtotal"] == "50000.00"
    assert cuerpo["descuento"] == "5000.00"
    assert cuerpo["total"] == "45000.00"


async def test_un_descuento_no_puede_superar_la_venta(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Una venta no puede terminar en negativo."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {"descripcion": "Remera", "cantidad": 1, "precio_unitario": "25000.00"}
            ],
            "descuento": "30000.00",
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "1.00"}],
        },
    )
    assert respuesta.status_code == 400


# ── Cobros y caja ─────────────────────────────────────────────────────────────


async def test_lo_cobrado_tiene_que_dar_el_total(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Un cobro de menos deja una venta a medias; uno de más descuadra el arqueo."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {
                    "descripcion": "Campera",
                    "cantidad": 1,
                    "precio_unitario": "100000.00",
                }
            ],
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "90000.00"}],
        },
    )
    assert respuesta.status_code == 400
    assert "no coincide" in respuesta.json()["detail"]


async def test_una_venta_pagada_con_dos_medios(
    client_vendedor: AsyncClient, efectivo: MedioPago, qr: MedioPago
) -> None:
    """Mitad efectivo y mitad QR es como se paga de verdad en un mostrador."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {
                    "descripcion": "Campera",
                    "cantidad": 1,
                    "precio_unitario": "100000.00",
                }
            ],
            "pagos": [
                {"medio_pago_id": str(efectivo.id), "importe": "40000.00"},
                {"medio_pago_id": str(qr.id), "importe": "60000.00"},
            ],
        },
    )
    assert respuesta.status_code == 201
    cobros = respuesta.json()["cobros"]
    assert {c["medio_pago"]: c["importe"] for c in cobros} == {
        "Efectivo": "40000.00",
        "QR": "60000.00",
    }


async def test_el_cobro_en_efectivo_entra_al_cajon(
    client_vendedor: AsyncClient, db: AsyncSession, efectivo: MedioPago
) -> None:
    """Es la razón de que la venta necesite una caja abierta."""
    await _abrir_caja(client_vendedor, "20000.00")
    await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))

    sesion = await caja_service.sesion_abierta(db)
    assert sesion is not None
    assert await caja_service.efectivo_en_caja(db, sesion.id) == Decimal("70000.00")


async def test_el_cobro_con_qr_no_entra_al_cajon(
    client_vendedor: AsyncClient, db: AsyncSession, efectivo: MedioPago, qr: MedioPago
) -> None:
    """Esa plata acredita en la cuenta días después, no está en el cajón."""
    await _abrir_caja(client_vendedor, "20000.00")
    await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {"descripcion": "Campera", "cantidad": 1, "precio_unitario": "50000.00"}
            ],
            "pagos": [{"medio_pago_id": str(qr.id), "importe": "50000.00"}],
        },
    )
    sesion = await caja_service.sesion_abierta(db)
    assert sesion is not None
    assert await caja_service.efectivo_en_caja(db, sesion.id) == Decimal("20000.00")


async def test_el_cobro_aparece_en_la_caja_con_el_numero_de_venta(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Desde la caja se puede saber de qué venta salió cada peso."""
    await _abrir_caja(client_vendedor)
    await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))

    caja = (await client_vendedor.get("/caja/actual")).json()
    cobro = caja["movimientos"][-1]
    assert cobro["tipo"] == "COBRO"
    assert cobro["concepto"] == "Venta #1"
    assert cobro["documento_tipo"] == "VENTA"


async def test_un_medio_de_pago_dado_de_baja_no_se_puede_usar(
    client_vendedor: AsyncClient, client_admin: AsyncClient, qr: MedioPago
) -> None:
    """Y el mensaje dice cuál es, no solo que algo está mal."""
    await _abrir_caja(client_vendedor)
    await client_admin.patch(f"/medios-pago/{qr.id}", json={"activo": False})
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {"descripcion": "Campera", "cantidad": 1, "precio_unitario": "1000.00"}
            ],
            "pagos": [{"medio_pago_id": str(qr.id), "importe": "1000.00"}],
        },
    )
    assert respuesta.status_code == 400
    assert "QR" in respuesta.json()["detail"]


# ── Anulación ─────────────────────────────────────────────────────────────────


async def test_anular_devuelve_la_plata_a_la_caja(
    client_vendedor: AsyncClient, db: AsyncSession, efectivo: MedioPago
) -> None:
    """El arqueo tiene que seguir cuadrando después de anular."""
    await _abrir_caja(client_vendedor, "20000.00")
    venta = await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))
    venta_id = venta.json()["id"]

    respuesta = await client_vendedor.post(
        f"/ventas/{venta_id}/anulacion", json={"motivo": "Se cargó mal"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ANULADA"

    sesion = await caja_service.sesion_abierta(db)
    assert sesion is not None
    assert await caja_service.efectivo_en_caja(db, sesion.id) == Decimal("20000.00")


async def test_la_venta_anulada_no_se_borra(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Queda con quién la anuló y por qué: es lo que se va a preguntar después."""
    await _abrir_caja(client_vendedor)
    venta = await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))
    venta_id = venta.json()["id"]
    await client_vendedor.post(
        f"/ventas/{venta_id}/anulacion", json={"motivo": "El cliente se arrepintió"}
    )

    releida = (await client_vendedor.get(f"/ventas/{venta_id}")).json()
    assert releida["motivo_anulacion"] == "El cliente se arrepintió"
    assert releida["anulada_por_nombre"] == "Vendedor Prueba"
    assert releida["total"] == "50000.00"
    assert len(releida["lineas"]) == 1


async def test_la_anulacion_deja_los_cobros_al_reves(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """El cobro original no se borra: se le suma la reversión."""
    await _abrir_caja(client_vendedor)
    venta = await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))
    venta_id = venta.json()["id"]
    respuesta = await client_vendedor.post(
        f"/ventas/{venta_id}/anulacion", json={"motivo": "Se cargó mal"}
    )
    cobros = respuesta.json()["cobros"]
    assert [c["importe"] for c in cobros] == ["50000.00", "-50000.00"]
    assert [c["es_reversion"] for c in cobros] == [False, True]


async def test_no_se_anula_dos_veces(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Si no, la plata volvería a la caja cada vez."""
    await _abrir_caja(client_vendedor)
    venta = await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))
    venta_id = venta.json()["id"]
    await client_vendedor.post(
        f"/ventas/{venta_id}/anulacion", json={"motivo": "Se cargó mal"}
    )
    respuesta = await client_vendedor.post(
        f"/ventas/{venta_id}/anulacion", json={"motivo": "De nuevo"}
    )
    assert respuesta.status_code == 409


async def test_la_anulacion_necesita_motivo(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Deshacer una venta cobrada tiene que quedar explicado."""
    await _abrir_caja(client_vendedor)
    venta = await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))
    respuesta = await client_vendedor.post(
        f"/ventas/{venta.json()['id']}/anulacion", json={"motivo": ""}
    )
    assert respuesta.status_code == 422


async def test_anular_una_venta_de_una_caja_ya_cerrada(
    client_vendedor: AsyncClient, db: AsyncSession, efectivo: MedioPago
) -> None:
    """La reversión va a la caja de ahora, no a la de la venta original.

    Si fuera a la original y esa caja estuviera cerrada, se estaría tocando un
    arqueo congelado: el número que alguien contó y firmó dejaría de coincidir
    con sus movimientos. Es el mismo criterio de una nota de crédito, que se
    emite el día que se emite.
    """
    await _abrir_caja(client_vendedor, "20000.00")
    venta = await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))
    venta_id = venta.json()["id"]
    original = (await db.execute(select(Venta))).scalars().first()
    assert original is not None
    id_original = original.sesion_caja_id

    await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "70000.00", "fondo_a_dejar": "20000.00"},
    )
    await _abrir_caja(client_vendedor, "20000.00")

    respuesta = await client_vendedor.post(
        f"/ventas/{venta_id}/anulacion", json={"motivo": "Devolución de ayer"}
    )
    assert respuesta.status_code == 200

    nueva = await caja_service.sesion_abierta(db)
    assert nueva is not None
    assert nueva.id != id_original
    # La caja de hoy quedó con 20.000 de fondo menos los 50.000 devueltos.
    assert await caja_service.efectivo_en_caja(db, nueva.id) == Decimal("-30000.00")


async def test_no_se_anula_sin_caja_abierta(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """La plata tiene que volver a alguna caja."""
    await _abrir_caja(client_vendedor, "20000.00")
    venta = await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))
    await client_vendedor.post(
        "/caja/cierre",
        json={"efectivo_declarado": "70000.00", "fondo_a_dejar": "20000.00"},
    )
    respuesta = await client_vendedor.post(
        f"/ventas/{venta.json()['id']}/anulacion", json={"motivo": "Se cargó mal"}
    )
    assert respuesta.status_code == 409


# ── Catálogo y listado ────────────────────────────────────────────────────────


async def test_el_vendedor_usa_el_catalogo_pero_no_lo_edita(
    client_vendedor: AsyncClient, articulo: Articulo
) -> None:
    """El mostrador necesita ver los artículos; cargarlos es del encargado."""
    assert (await client_vendedor.get("/articulos")).status_code == 200
    respuesta = await client_vendedor.post(
        "/articulos", json={"nombre": "Gorra", "precio": "20000.00"}
    )
    assert respuesta.status_code == 403


async def test_se_busca_una_venta_por_numero_o_por_lo_que_dice(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """En el mostrador se busca "la campera de ayer", no un identificador."""
    await _abrir_caja(client_vendedor)
    await client_vendedor.post(
        "/ventas", json=_venta(efectivo, "50000.00", "Campera azul")
    )
    await client_vendedor.post(
        "/ventas", json=_venta(efectivo, "20000.00", "Gorra negra")
    )

    por_texto = (
        await client_vendedor.get("/ventas", params={"buscar": "campera"})
    ).json()
    assert len(por_texto) == 1
    assert por_texto[0]["numero"] == 1

    por_numero = (await client_vendedor.get("/ventas", params={"buscar": "#2"})).json()
    assert len(por_numero) == 1
    assert por_numero[0]["numero"] == 2


async def test_el_listado_cuenta_los_articulos_vendidos(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Para ver de un vistazo si fue una venta grande o chica."""
    await _abrir_caja(client_vendedor)
    await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [
                {"descripcion": "Remera", "cantidad": 3, "precio_unitario": "10000.00"},
                {"descripcion": "Gorra", "cantidad": 2, "precio_unitario": "5000.00"},
            ],
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "40000.00"}],
        },
    )
    fila = (await client_vendedor.get("/ventas")).json()[0]
    assert fila["cantidad_articulos"] == 5


async def test_los_importes_viajan_como_texto(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Los decimales de JavaScript no representan exactamente los centavos."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.55"))
    assert respuesta.json()["total"] == "50000.55"


async def test_una_venta_sin_lineas_no_es_una_venta(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """El mínimo de una venta es que diga qué se vendió."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [],
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "1.00"}],
        },
    )
    assert respuesta.status_code == 422


async def test_una_linea_tiene_que_decir_que_se_vendio(
    client_vendedor: AsyncClient, efectivo: MedioPago
) -> None:
    """Sin artículo y sin descripción, la línea no dice nada."""
    await _abrir_caja(client_vendedor)
    respuesta = await client_vendedor.post(
        "/ventas",
        json={
            "lineas": [{"cantidad": 1, "precio_unitario": "1000.00"}],
            "pagos": [{"medio_pago_id": str(efectivo.id), "importe": "1000.00"}],
        },
    )
    assert respuesta.status_code == 422


async def test_registrar_una_venta_deja_su_rastro_de_auditoria(
    client_vendedor: AsyncClient, client_admin: AsyncClient, efectivo: MedioPago
) -> None:
    """La auditoría automática también cubre las ventas, sin hacer nada."""
    await _abrir_caja(client_vendedor)
    await client_vendedor.post("/ventas", json=_venta(efectivo, "50000.00"))
    entradas = (await client_admin.get("/audit-log", params={"tabla": "venta"})).json()
    assert len(entradas) >= 1
    assert entradas[0]["operacion"] == "CREATE"
