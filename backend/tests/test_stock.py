"""Existencias, movimientos, ingresos, ajustes y alertas."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.producto import Variante
from app.models.stock import MovimientoStock, Stock, TipoMovimiento
from app.models.sucursal import Sucursal
from app.services import stock_service


async def test_una_prenda_recien_cargada_no_tiene_existencias(
    client_admin: AsyncClient, variante: Variante
) -> None:
    """La fila de stock nace con el primer movimiento, no con la prenda.

    Crear una fila en cero por cada combinación de prenda y sucursal al dar de
    alta el catálogo llenaría la tabla de ceros que no dicen nada.
    """
    respuesta = await client_admin.get(f"/stock/variante/{variante.id}")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


async def test_ingreso_de_mercaderia(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Lo que llega al local se suma al stock."""
    respuesta = await client_admin.post(
        "/stock/ingresos",
        json={
            "variante_id": str(variante.id),
            "sucursal_id": str(sucursal.id),
            "cantidad": 12,
            "motivo": "Pedido de temporada",
        },
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["cantidad"] == 12
    assert cuerpo["producto"] == "Remera lisa"
    assert cuerpo["talle"] == "M"


async def test_el_ingreso_deja_su_movimiento(
    client_admin: AsyncClient, db: AsyncSession, variante: Variante, sucursal: Sucursal
) -> None:
    """Toda variación deja constancia de qué pasó, cuándo y por qué."""
    await client_admin.post(
        "/stock/ingresos",
        json={
            "variante_id": str(variante.id),
            "sucursal_id": str(sucursal.id),
            "cantidad": 5,
            "motivo": "Pedido de temporada",
        },
    )
    movimientos = (await client_admin.get("/stock/movimientos")).json()
    assert len(movimientos) == 1
    assert movimientos[0]["tipo"] == "INGRESO"
    assert movimientos[0]["cantidad"] == 5
    assert movimientos[0]["cantidad_resultante"] == 5
    assert movimientos[0]["motivo"] == "Pedido de temporada"


async def test_el_movimiento_registra_quien_lo_hizo(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """El "quién" sale de la auditoría automática, sin que el service lo escriba."""
    await client_admin.post(
        "/stock/ingresos",
        json={
            "variante_id": str(variante.id),
            "sucursal_id": str(sucursal.id),
            "cantidad": 3,
            "motivo": "Reposición",
        },
    )
    movimientos = (await client_admin.get("/stock/movimientos")).json()
    assert movimientos[0]["usuario_id"] is not None


async def test_ajustar_deja_la_cantidad_contada(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Es la operación de "conté y hay 7"."""
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 10, "motivo": "Ingreso"}
    )
    respuesta = await client_admin.post(
        "/stock/ajustes",
        json={**cuerpo, "cantidad_final": 7, "motivo": "Conteo del lunes"},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["cantidad"] == 7


async def test_el_ajuste_guarda_la_diferencia_no_el_total(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Lo que hay que poder explicar después es cuánto cambió, no cuánto quedó."""
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 10, "motivo": "Ingreso"}
    )
    await client_admin.post(
        "/stock/ajustes",
        json={**cuerpo, "cantidad_final": 7, "motivo": "Faltaban tres"},
    )
    ajustes = (
        await client_admin.get("/stock/movimientos", params={"tipo": "AJUSTE"})
    ).json()
    assert ajustes[0]["cantidad"] == -3
    assert ajustes[0]["cantidad_resultante"] == 7


async def test_un_ajuste_sin_diferencia_no_ensucia_el_historial(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Contar y que dé lo mismo no es un movimiento."""
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 4, "motivo": "Ingreso"}
    )
    await client_admin.post(
        "/stock/ajustes", json={**cuerpo, "cantidad_final": 4, "motivo": "Conteo"}
    )
    ajustes = (
        await client_admin.get("/stock/movimientos", params={"tipo": "AJUSTE"})
    ).json()
    assert ajustes == []


async def test_el_ajuste_necesita_un_motivo(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Un ajuste sin motivo es un número que nadie va a poder explicar."""
    respuesta = await client_admin.post(
        "/stock/ajustes",
        json={
            "variante_id": str(variante.id),
            "sucursal_id": str(sucursal.id),
            "cantidad_final": 3,
            "motivo": "",
        },
    )
    assert respuesta.status_code == 422


async def test_el_vendedor_consulta_pero_no_ajusta(
    client_vendedor: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """El mostrador necesita ver qué hay; corregirlo es del encargado."""
    assert (await client_vendedor.get("/stock")).status_code == 200
    respuesta = await client_vendedor.post(
        "/stock/ajustes",
        json={
            "variante_id": str(variante.id),
            "sucursal_id": str(sucursal.id),
            "cantidad_final": 999,
            "motivo": "Probando",
        },
    )
    assert respuesta.status_code == 403


async def test_el_encargado_si_ajusta(
    client_encargado: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Corregir existencias es parte de manejar el local."""
    respuesta = await client_encargado.post(
        "/stock/ajustes",
        json={
            "variante_id": str(variante.id),
            "sucursal_id": str(sucursal.id),
            "cantidad_final": 5,
            "motivo": "Conteo",
        },
    )
    assert respuesta.status_code == 201


# ── La regla que sostiene todo el módulo ─────────────────────────────────────


async def test_el_saldo_coincide_con_la_suma_de_los_movimientos(
    client_admin: AsyncClient, db: AsyncSession, variante: Variante, sucursal: Sucursal
) -> None:
    """Después de una tanda de movimientos, las dos formas de contar dan igual.

    Es la razón de ser de tener saldo y movimientos a la vez (D-3).
    """
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 20, "motivo": "Pedido"}
    )
    await client_admin.post(
        "/stock/ajustes", json={**cuerpo, "cantidad_final": 18, "motivo": "Rotas"}
    )
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 6, "motivo": "Reposición"}
    )

    guardado = await stock_service.cantidad_actual(db, variante.id, sucursal.id)
    sumado = await stock_service.cantidad_por_movimientos(db, variante.id, sucursal.id)
    assert guardado == sumado == 24


async def test_el_control_no_encuentra_diferencias_cuando_todo_esta_bien(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """El control tiene que dar vacío siempre."""
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 9, "motivo": "Pedido"}
    )
    assert (await client_admin.get("/stock/control")).json() == []


async def test_el_control_encuentra_un_saldo_corrompido(
    client_admin: AsyncClient, db: AsyncSession, variante: Variante, sucursal: Sucursal
) -> None:
    """Si alguien toca el saldo sin registrar el movimiento, se nota.

    Se simula acá lo que sería un error en un módulo futuro que actualice el
    stock por su cuenta en vez de pasar por `registrar_movimiento`. El sistema
    tiene que poder señalar exactamente qué prenda dejó de cuadrar.
    """
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 9, "motivo": "Pedido"}
    )

    fila = (
        await db.execute(select(Stock).where(Stock.variante_id == variante.id))
    ).scalar_one()
    fila.cantidad = 99
    await db.flush()

    diferencias = (await client_admin.get("/stock/control")).json()
    assert len(diferencias) == 1
    assert diferencias[0]["cantidad_guardada"] == 99
    assert diferencias[0]["cantidad_por_movimientos"] == 9
    assert diferencias[0]["sku"] == "NIKREMLIS-M-NEG"


async def test_el_control_es_solo_del_administrador(
    client_encargado: AsyncClient,
) -> None:
    """Es una herramienta de diagnóstico, no una pantalla del día a día."""
    assert (await client_encargado.get("/stock/control")).status_code == 403


# ── Vender sin stock ──────────────────────────────────────────────────────────


async def test_no_se_puede_sacar_mas_de_lo_que_hay(
    db: AsyncSession, variante: Variante, sucursal: Sucursal
) -> None:
    """Por decisión del dueño, la salida que dejaría negativo se rechaza."""
    await stock_service.registrar_movimiento(
        db,
        variante_id=variante.id,
        sucursal_id=sucursal.id,
        tipo=TipoMovimiento.ingreso,
        cantidad=2,
        motivo="Ingreso",
    )
    with pytest.raises(stock_service.StockInsuficienteError) as fallo:
        await stock_service.registrar_movimiento(
            db,
            variante_id=variante.id,
            sucursal_id=sucursal.id,
            tipo=TipoMovimiento.venta,
            cantidad=-3,
        )
    assert fallo.value.disponible == 2
    assert fallo.value.pedido == 3


async def test_el_rechazo_no_deja_rastro_de_stock(
    db: AsyncSession, variante: Variante, sucursal: Sucursal
) -> None:
    """Una venta rechazada no puede haber movido el saldo."""
    await stock_service.registrar_movimiento(
        db,
        variante_id=variante.id,
        sucursal_id=sucursal.id,
        tipo=TipoMovimiento.ingreso,
        cantidad=2,
        motivo="Ingreso",
    )
    with pytest.raises(stock_service.StockInsuficienteError):
        await stock_service.registrar_movimiento(
            db,
            variante_id=variante.id,
            sucursal_id=sucursal.id,
            tipo=TipoMovimiento.venta,
            cantidad=-3,
        )
    assert await stock_service.cantidad_actual(db, variante.id, sucursal.id) == 2


async def test_con_el_parametro_encendido_se_permite_el_negativo(
    db: AsyncSession, variante: Variante, sucursal: Sucursal
) -> None:
    """Cambiar de opinión es una variable de entorno, no reescribir el circuito."""
    original = settings.permitir_stock_negativo
    settings.permitir_stock_negativo = True
    try:
        movimiento = await stock_service.registrar_movimiento(
            db,
            variante_id=variante.id,
            sucursal_id=sucursal.id,
            tipo=TipoMovimiento.venta,
            cantidad=-3,
        )
        assert movimiento.cantidad_resultante == -3
    finally:
        settings.permitir_stock_negativo = original


async def test_un_ajuste_a_la_baja_nunca_se_rechaza(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Si se contó menos, la prenda ya no está: rechazar no la trae de vuelta."""
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 3, "motivo": "Ingreso"}
    )
    respuesta = await client_admin.post(
        "/stock/ajustes", json={**cuerpo, "cantidad_final": 0, "motivo": "No aparecen"}
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["cantidad"] == 0


# ── Alertas de mínimo ─────────────────────────────────────────────────────────


async def test_alerta_cuando_se_llega_al_minimo(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """La pantalla que se mira antes de pedirle al proveedor."""
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post("/stock/minimo", json={**cuerpo, "stock_minimo": 3})
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 10, "motivo": "Pedido"}
    )
    assert (await client_admin.get("/stock/alertas")).json() == []

    await client_admin.post(
        "/stock/ajustes", json={**cuerpo, "cantidad_final": 3, "motivo": "Ventas"}
    )
    alertas = (await client_admin.get("/stock/alertas")).json()
    assert len(alertas) == 1
    assert alertas[0]["bajo_minimo"] is True


async def test_sin_minimo_definido_no_hay_alerta(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Con mínimo en cero no se controla nada.

    Si no fuera así, cada prenda agotada del catálogo aparecería en rojo,
    incluidas las de temporada pasada que ya no se reponen, y la pantalla de
    alertas dejaría de servir para decidir un pedido.
    """
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 1, "motivo": "Ingreso"}
    )
    await client_admin.post(
        "/stock/ajustes", json={**cuerpo, "cantidad_final": 0, "motivo": "Vendidas"}
    )
    assert (await client_admin.get("/stock/alertas")).json() == []


async def test_el_minimo_se_puede_fijar_antes_de_que_llegue_la_mercaderia(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Es la forma de que la prenda aparezca en las alertas desde el primer día."""
    respuesta = await client_admin.post(
        "/stock/minimo",
        json={
            "variante_id": str(variante.id),
            "sucursal_id": str(sucursal.id),
            "stock_minimo": 5,
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["cantidad"] == 0
    assert respuesta.json()["bajo_minimo"] is True


# ── Filtros ───────────────────────────────────────────────────────────────────


async def test_el_listado_filtra_por_texto_y_por_sucursal(
    client_admin: AsyncClient, variante: Variante, sucursal: Sucursal
) -> None:
    """Se busca por nombre de prenda o por su código."""
    cuerpo = {"variante_id": str(variante.id), "sucursal_id": str(sucursal.id)}
    await client_admin.post(
        "/stock/ingresos", json={**cuerpo, "cantidad": 4, "motivo": "Ingreso"}
    )

    assert (
        len((await client_admin.get("/stock", params={"buscar": "Remera"})).json()) == 1
    )
    assert (
        len((await client_admin.get("/stock", params={"buscar": "NIKREM"})).json()) == 1
    )
    assert (
        len((await client_admin.get("/stock", params={"buscar": "campera"})).json())
        == 0
    )
    assert (
        len(
            (
                await client_admin.get(
                    "/stock", params={"sucursal_id": str(sucursal.id)}
                )
            ).json()
        )
        == 1
    )


async def test_el_stock_es_por_sucursal(
    client_admin: AsyncClient, db: AsyncSession, variante: Variante, sucursal: Sucursal
) -> None:
    """La misma prenda en dos locales son dos existencias distintas.

    Es lo que permite contestar "¿la tenés acá?" y no solo "¿la tenemos?".
    """
    otra = Sucursal(nombre="Sucursal Norte", codigo="NOR", activa=True)
    db.add(otra)
    await db.flush()

    base = {"variante_id": str(variante.id)}
    await client_admin.post(
        "/stock/ingresos",
        json={
            **base,
            "sucursal_id": str(sucursal.id),
            "cantidad": 4,
            "motivo": "Pedido",
        },
    )
    await client_admin.post(
        "/stock/ingresos",
        json={**base, "sucursal_id": str(otra.id), "cantidad": 9, "motivo": "Pedido"},
    )

    filas = (await client_admin.get(f"/stock/variante/{variante.id}")).json()
    assert {f["sucursal"]: f["cantidad"] for f in filas} == {
        "Local de prueba": 4,
        "Sucursal Norte": 9,
    }


async def test_una_prenda_que_no_existe_se_rechaza(
    client_admin: AsyncClient, sucursal: Sucursal
) -> None:
    """No se puede ingresar mercadería de algo que no está en el catálogo."""
    respuesta = await client_admin.post(
        "/stock/ingresos",
        json={
            "variante_id": "00000000-0000-0000-0000-000000000000",
            "sucursal_id": str(sucursal.id),
            "cantidad": 1,
            "motivo": "Probando",
        },
    )
    assert respuesta.status_code == 400


async def test_un_movimiento_de_cero_no_tiene_sentido(
    db: AsyncSession, variante: Variante, sucursal: Sucursal
) -> None:
    """Registrar cero unidades sería una fila que no dice nada."""
    with pytest.raises(ValueError, match="cero"):
        await stock_service.registrar_movimiento(
            db,
            variante_id=variante.id,
            sucursal_id=sucursal.id,
            tipo=TipoMovimiento.ingreso,
            cantidad=0,
        )


async def test_los_movimientos_no_se_pueden_borrar_por_la_api(
    client_admin: AsyncClient, db: AsyncSession, variante: Variante, sucursal: Sucursal
) -> None:
    """El movimiento es un hecho: se corrige con otro movimiento, no borrando.

    No hay endpoint para borrarlo, y este test lo deja escrito: si algún día
    alguien agrega uno, esto se pone en rojo y obliga a discutirlo.
    """
    from app.main import app

    rutas = {
        ruta
        for ruta, metodos in app.openapi()["paths"].items()
        if "delete" in metodos and "movimiento" in ruta
    }
    assert rutas == set()
    assert MovimientoStock.__tablename__ == "movimiento_stock"


async def test_el_listado_filtra_por_prenda(
    client_admin: AsyncClient,
    db: AsyncSession,
    variante: Variante,
    sucursal: Sucursal,
) -> None:
    """La pantalla de una prenda pide todas sus existencias de una sola vez.

    Sin este filtro habría que preguntar variante por variante, y una remera
    con cuatro talles y tres colores serían doce consultas para dibujar una
    tabla.
    """
    await client_admin.post(
        "/stock/ingresos",
        json={
            "variante_id": str(variante.id),
            "sucursal_id": str(sucursal.id),
            "cantidad": 4,
            "motivo": "Ingreso",
        },
    )
    filas = (
        await client_admin.get(
            "/stock", params={"producto_id": str(variante.producto_id)}
        )
    ).json()
    assert len(filas) == 1
    assert filas[0]["sku"] == "NIKREMLIS-M-NEG"
