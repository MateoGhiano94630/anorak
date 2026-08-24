"""
La auditoría se escribe sola.

Estos tests son la red que sostiene la regla: ningún service llama a nada
para registrar lo que hizo, así que lo único que garantiza que el rastro
exista es el listener de `before_flush`. Si alguno de estos se pone en rojo,
el sistema dejó de poder contestar quién tocó qué.

El sujeto de prueba es `usuario` porque es la única tabla de negocio que hay
hoy, pero el listener no sabe nada de usuarios: registra cualquier tabla.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.audit_log import AuditLog, OperacionAudit
from app.models.usuario import RolUsuario, Usuario


async def _auditoria_de(db: AsyncSession, tabla: str) -> list[AuditLog]:
    """Devuelve las entradas de auditoría de una tabla, de la más vieja."""
    resultado = await db.execute(
        select(AuditLog).where(AuditLog.tabla_afectada == tabla).order_by(AuditLog.ts)
    )
    return list(resultado.scalars().all())


def _nuevo_usuario(email: str = "nuevo@prueba.com.ar") -> Usuario:
    """Un usuario cualquiera, para usar como fila auditada."""
    return Usuario(
        nombre="Nuevo",
        email=email,
        password_hash=hash_password("clave12345"),
        rol=RolUsuario.vendedor,
        activo=True,
    )


async def test_un_alta_deja_su_registro(db: AsyncSession) -> None:
    """Crear una fila cualquiera genera una entrada CREATE con la foto entera."""
    db.add(_nuevo_usuario())
    await db.flush()

    entradas = await _auditoria_de(db, "usuario")
    assert len(entradas) == 1
    assert entradas[0].operacion == OperacionAudit.create
    assert entradas[0].datos_nuevos is not None
    assert entradas[0].datos_nuevos["email"] == "nuevo@prueba.com.ar"


async def test_un_cambio_guarda_solo_lo_que_cambio(
    db: AsyncSession, usuario_vendedor: Usuario
) -> None:
    """El UPDATE registra la diferencia, no la fila entera.

    El `refresh` no es decorativo: deja la fila con todas sus columnas leídas,
    que es como llega cualquier objeto que un endpoint trajo de la base. Sin
    eso, SQLAlchemy no tiene el valor anterior de una columna que nunca leyó
    (ver el docstring de `_diff` en app/core/audit.py).
    """
    await db.refresh(usuario_vendedor)
    usuario_vendedor.nombre = "Vendedor Renombrado"
    await db.flush()

    cambios = [
        e
        for e in await _auditoria_de(db, "usuario")
        if e.operacion == OperacionAudit.update
    ]
    assert len(cambios) == 1
    assert cambios[0].datos_anteriores == {"nombre": "Vendedor Prueba"}
    assert cambios[0].datos_nuevos is not None
    assert cambios[0].datos_nuevos["nombre"] == "Vendedor Renombrado"
    # No aparecen las columnas que nadie tocó.
    assert "email" not in cambios[0].datos_nuevos


async def test_una_baja_guarda_la_foto_previa(
    db: AsyncSession, usuario_vendedor: Usuario
) -> None:
    """Borrar deja constancia de lo que había antes de borrarse."""
    await db.delete(usuario_vendedor)
    await db.flush()

    bajas = [
        e
        for e in await _auditoria_de(db, "usuario")
        if e.operacion == OperacionAudit.delete
    ]
    assert len(bajas) == 1
    assert bajas[0].datos_anteriores is not None
    assert bajas[0].datos_anteriores["email"] == "vendedor@prueba.com.ar"


async def test_la_contrasena_nunca_queda_en_la_auditoria(db: AsyncSession) -> None:
    """El hash de la contraseña se redacta, incluso siendo un hash."""
    db.add(_nuevo_usuario())
    await db.flush()

    entradas = await _auditoria_de(db, "usuario")
    assert entradas[-1].datos_nuevos is not None
    assert entradas[-1].datos_nuevos["password_hash"] == "***"


async def test_la_auditoria_no_se_audita_a_si_misma(db: AsyncSession) -> None:
    """Sin esta exclusión el listener se llamaría a sí mismo sin fin."""
    db.add(_nuevo_usuario())
    await db.flush()
    assert await _auditoria_de(db, "audit_log") == []


async def test_una_escritura_del_sistema_queda_sin_usuario(db: AsyncSession) -> None:
    """Lo que escribe el propio sistema (seed, migración) no tiene autor."""
    db.add(_nuevo_usuario())
    await db.flush()
    assert (await _auditoria_de(db, "usuario"))[0].usuario_id is None


async def test_por_la_api_queda_registrado_quien_escribio(
    client_admin: AsyncClient, usuario_admin: Usuario, db: AsyncSession
) -> None:
    """Un alta hecha desde la API queda atribuida al usuario de la sesión."""
    respuesta = await client_admin.post(
        "/usuarios",
        json={
            "nombre": "Sofía",
            "email": "sofia@prueba.com.ar",
            "password": "clave12345",
            "rol": "VENDEDOR",
        },
    )
    assert respuesta.status_code == 201

    entrada = next(
        e
        for e in await _auditoria_de(db, "usuario")
        if e.datos_nuevos is not None
        and e.datos_nuevos["email"] == "sofia@prueba.com.ar"
    )
    assert entrada.usuario_id == usuario_admin.id


async def test_los_sellos_de_autoria_se_completan_solos(
    client_admin: AsyncClient, usuario_admin: Usuario, db: AsyncSession
) -> None:
    """`created_by` y `updated_by` los pone el sistema, no el service."""
    respuesta = await client_admin.post(
        "/usuarios",
        json={
            "nombre": "Sofía",
            "email": "sofia@prueba.com.ar",
            "password": "clave12345",
            "rol": "VENDEDOR",
        },
    )
    creado = await db.get(Usuario, respuesta.json()["id"])
    assert creado is not None
    assert creado.created_by == usuario_admin.id
    assert creado.updated_by == usuario_admin.id


async def test_una_lectura_no_ensucia_la_auditoria(
    client_admin: AsyncClient, usuario_vendedor: Usuario, db: AsyncSession
) -> None:
    """Consultar no genera entradas: solo se registra lo que cambia."""
    antes = len(await _auditoria_de(db, "usuario"))
    await client_admin.get("/usuarios")
    await client_admin.get("/usuarios")
    assert len(await _auditoria_de(db, "usuario")) == antes


async def test_un_cambio_por_la_api_guarda_el_valor_anterior(
    client_admin: AsyncClient, usuario_vendedor: Usuario, db: AsyncSession
) -> None:
    """Lo que se cambia desde una pantalla queda con el "antes" y el "después".

    Es el caso que de verdad importa: el día que haya que explicar por qué
    alguien pudo hacer algo, la pregunta va a ser desde qué rol cambió, no
    solo en cuál quedó.
    """
    await client_admin.patch(
        f"/usuarios/{usuario_vendedor.id}", json={"rol": "ENCARGADO"}
    )

    cambios = [
        e
        for e in await _auditoria_de(db, "usuario")
        if e.operacion == OperacionAudit.update
    ]
    assert cambios[-1].datos_anteriores == {"rol": "VENDEDOR"}
    assert cambios[-1].datos_nuevos is not None
    assert cambios[-1].datos_nuevos["rol"] == "ENCARGADO"


async def test_el_registro_de_auditoria_es_solo_para_el_admin(
    client_vendedor: AsyncClient,
) -> None:
    """El vendedor no ve el rastro de auditoría."""
    assert (await client_vendedor.get("/audit-log")).status_code == 403


async def test_el_admin_consulta_el_registro_filtrando_por_tabla(
    client_admin: AsyncClient,
) -> None:
    """La consulta se puede acotar a una tabla."""
    await client_admin.post(
        "/usuarios",
        json={
            "nombre": "Sofía",
            "email": "sofia@prueba.com.ar",
            "password": "clave12345",
            "rol": "VENDEDOR",
        },
    )
    respuesta = await client_admin.get("/audit-log", params={"tabla": "usuario"})
    assert respuesta.status_code == 200
    assert all(e["tabla_afectada"] == "usuario" for e in respuesta.json())
    assert len(respuesta.json()) >= 1
