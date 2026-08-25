# Estado del sistema

Qué está hecho, qué está a medias y qué falta. Este archivo se actualiza al
cerrar cada tanda, y dice la verdad aunque sea incómoda: un "listo" que no lo
está cuesta más caro que un pendiente anotado.

**Última actualización**: 24/08/2026 — módulo de ventas.

---

## 1. Resumen

| | |
|---|---|
| Estado | Base + caja + ventas funcionando |
| Última tanda cerrada | 3 (ventas) |
| Próxima | A definir |
| Tests backend | 95, todos en verde |
| Tests frontend | 30 unitarios + 3 de punta a punta (por 2 dispositivos) |
| Migraciones | 3, aplicadas. Sin pendientes |
| CI | Escrito y completo. **Todavía no corrió en GitHub**: el repositorio es local |
| Despliegue | **No desplegado.** Ni Railway ni Cloudflare Pages están configurados |

---

## 2. Qué pasó el 24/08/2026

Se quitaron los módulos de catálogo, precios, stock y sucursales. El análisis
del que salieron era equivocado, así que el modelo de negocio que
implementaban no sirve.

**No se empezó de cero, y a propósito.** Lo que quedó no depende de qué se
venda: los tipos portables (`UUIDType`, `FlexibleJSON`, `enum_texto`), el
listener de auditoría, el arnés de tests, `<Listado>`, `<CampoFecha>`, el
sistema de ayuda, el CI y los archivos de despliegue. Rehacer todo eso habría
significado volver a pagar los errores que ya están documentados en
`CLAUDE.md`.

Lo retirado está en el historial de git, en los commits `Tanda 2` y `Tanda 3`.
`docs/arquitectura.md` §6 resume qué se aprendió de cada decisión, separando
lo que sigue valiendo (cómo modelar) de lo que quedó sin efecto (qué modelar).

También se quitó `usuario.sucursal_id`, porque la tabla a la que apuntaba ya
no existe.

---

## 3. Qué quedó funcionando

### Backend

- **Ingreso con JWT y bcrypt directo.** `POST /auth/login`, `GET /auth/me`,
  `POST /auth/cambiar-password`. Cada ingreso deja registrada la fecha.
- **Tres roles**: `ADMIN`, `ENCARGADO`, `VENDEDOR`. El admin es superset de
  todos los permisos y no hace falta nombrarlo en cada ruta. `EncargadoUser`
  existe en `app/core/deps.py` y hoy no tiene consumidor: es el andamiaje de
  permisos que va a usar el módulo que venga.
- **Usuarios**: alta, listado, modificación. Baja lógica. Un admin no se puede
  dar de baja a sí mismo. El hash de contraseña no sale nunca por la API.
- **Auditoría automática**: un listener sobre `before_flush` registra cada
  alta, cambio y baja de cualquier tabla y completa `created_by`/`updated_by`.
  Se lee por `GET /audit-log`, solo admin, con filtros. Es de solo lectura.
- **Seed idempotente**: crea la cuenta `admin@anorak.com.ar` con
  `SEED_PASSWORD`. Si la contraseña sigue siendo la de fábrica, el arranque
  avisa por log.
- **Chequeo de esquema** al arrancar, que loguea ERROR si la base no está al
  día sin frenar el arranque.

### Backend — caja (tanda 2)

- **Medios de pago** con su tipo, si entra al cajón, comisión y días de
  acreditación. El seed carga efectivo, débito, crédito, QR y transferencia.
- **Una sesión por jornada.** No se abre otra mientras haya una abierta, y el
  mensaje dice quién la abrió y cuándo.
- **Un solo punto de escritura**: `caja_service.registrar_movimiento()`. Una
  salida que dejaría el cajón en negativo se rechaza sin revelar cuánto hay.
- **Movimientos inmutables**, con número de renglón propio por sesión: el
  orden no puede salir de `created_at` (ver D-14).
- **Arqueo a ciegas**: mientras la caja está abierta la API no informa el
  efectivo esperado, ni en la sesión, ni en los totales, ni en los mensajes de
  error. El cierre lo revela después de declarar lo contado.
- **Cierre** que congela declarado, esperado y diferencia, anota la diferencia
  como movimiento y retira lo que sobra del fondo. Al terminar, la suma de los
  movimientos en efectivo es exactamente el fondo que quedó.
- **Historial de cierres** para encargado y administrador.

### Backend — ventas (tanda 3)

- **Catálogo opcional** de artículos: uno por modelo, con precio y categoría.
  El talle vive en la línea de la venta, no en el artículo.
- **Venta** con líneas que salen del catálogo o escritas a mano, descuentos
  por línea y sobre el total, y numeración correlativa propia (no fiscal).
- **La línea guarda la descripción y el precio con el que se vendió.** Hay un
  test que cambia el precio del artículo y comprueba que la venta no se mueve.
- **Cobro con varios medios de pago.** Lo cobrado tiene que dar exactamente el
  total: ni de menos ni de más.
- **Sin caja abierta no se vende** (409 con un mensaje que dice qué hacer).
  Cada cobro es un movimiento de caja que apunta a la venta; no hay tabla de
  pagos aparte.
- **Anulación** que no borra: marca la venta y genera las reversiones en la
  sesión **abierta ahora**, para no tocar un arqueo ya congelado.

### Frontend

- **Ingreso** con el token en memoria. Al recargar la pestaña hay que volver a
  entrar, y la ayuda de la pantalla lo explica.
- **Marco general**: menú filtrado por puesto, columna a la izquierda en
  pantalla ancha y fila deslizable en el celular.
- **Pantallas**: Inicio, Vender, Ventas, Caja, Cierres de caja, Catálogo,
  Medios de pago y Usuarios.
- **Componentes base**: `<Listado>` (tabla en pantalla ancha, tarjetas en
  angosta, desde una sola definición de columnas), `<CampoFecha>` (dd/mm/aaaa,
  sin `<input type="date">`), `<Campo>`, `<Selector>`, `<Boton>`, `<Ayuda>`.
- **Bibliotecas propias**: `lib/fecha.ts`, `lib/dinero.ts`, `lib/api.ts`,
  `lib/sesion.ts`, `lib/ayuda.ts`, `lib/etiquetas.ts`, `lib/tipos.ts`,
  `lib/importes.ts`, `lib/carrito.ts`.
- **Las cuentas del mostrador viven en `lib/carrito.ts`**, en centavos enteros
  y con tests: es la parte que no puede estar mal.

Probado a mano el 24/08/2026, dos veces:

1. Contra la API, después de la limpieza: ingreso con la cuenta del seed, alta
   de usuario, y lectura del registro de auditoría distinguiendo lo que
   escribió el sistema de lo que escribió una persona.
2. En un navegador real, con el frontend contra la API: apertura con el fondo
   sugerido, verificación de que en ninguna parte de la pantalla aparece el
   efectivo esperado, un ingreso, un gasto con comprobante, un retiro excesivo
   rechazado sin revelar el saldo, un cierre rechazado por no explicar la
   diferencia, y el cierre final revelando 61.500 esperado contra 61.000
   contado. Sin errores de consola más allá de los rechazos buscados.

---

## 4. Qué falta y hay que tener en cuenta

| # | Pendiente | Cuándo |
|---|---|---|
| P-1 | La venta **no descuenta existencias**: no hay control de stock. Fue una decisión, no un olvido | Cuando el local lo necesite |
| P-2 | El repositorio es local: no hay remoto en GitHub, así que el CI nunca corrió | Antes de la próxima tanda |
| P-3 | Nada está desplegado. El paso a paso está escrito en `docs/despliegue.md`; falta ejecutarlo | Cuando haya algo que mostrar |
| P-4 | `pre-commit install` no se corrió en la máquina de desarrollo | Antes del primer commit compartido |
| P-5 | El manual de usuario tiene las páginas de ingreso y usuarios. Falta publicarlo | Va creciendo con cada tanda |
| P-6 | La facturación está apagada (`ARCA_HABILITADO=false`) y sin certificados | Cuando el dueño los tenga |
| P-7 | Los tests de punta a punta del CI no levantan el backend, así que prueban el frontend solo | Evaluar un trabajo de CI que levante los dos |
| P-8 | La configuración de ARCA y R2 quedó declarada pero sin consumidor. `boto3`, `weasyprint`, `pillow` y `qrcode` siguen en las dependencias porque son parte del stack elegido | Se usan cuando vuelva a haber un módulo que los necesite |
| P-9 | La comisión y los días de acreditación de los medios de pago están vacíos: los tiene que cargar el dueño con los números de su contrato | Antes de conciliar contra el resumen del procesador |
| P-10 | No hay comprobante de cierre en PDF. Hoy el arqueo se ve en pantalla y queda en el historial | Cuando haga falta imprimirlo |
| P-11 | No hay ticket para el cliente. Después de cobrar se muestra el resumen en pantalla | El día que haya cambios con ticket obligatorio |
| P-12 | El mostrador necesita conexión para vender. Los identificadores ya se generan del lado del cliente, así que sumar la cola local después no obliga a migrar | Si la conexión del local resulta un problema |
| P-13 | Mientras haya líneas escritas a mano, "Campera azul" y "campera azul" son dos cosas para cualquier reporte. Es el costo de poder vender sin catálogo | Se atenúa cargando el catálogo |

---

## 5. Cosas que hay que saber antes de tocar algo

- **Las migraciones se autogeneran contra SQLite.** Funciona porque todos los
  tipos son portables, pero hay que **leer el archivo generado** antes de
  commitearlo, y después pasarle `black` y `ruff check --fix`, o el CI lo
  rechaza por formato.
- **Nunca declarar una columna de enum como `String`.** Va con `enum_texto()`
  de `app/core/types.py`. Con `String`, la fila leída de la base vuelve como
  `str` y los tests no lo detectan: el objeto recién creado en Python conserva
  el enum. Hay un test de regresión en `tests/test_usuarios.py`.
- **Los dominios de correo `.test` y `.local` no sirven.** `EmailStr` los
  rechaza por ser nombres de uso reservado. En los tests se usa
  `@prueba.com.ar` y en el seed `@anorak.com.ar`.
- **`created_by`/`updated_by` no tienen clave foránea**, a propósito. Ver D-3
  en `docs/arquitectura.md`.
- **Cada fixture de cliente HTTP abre el suyo.** No volver a la versión que
  compartía uno solo cambiándole el header: un test que pide `client_admin` y
  `client_vendedor` a la vez recibiría el mismo objeto, y los tests de
  permisos darían verde sin probar nada.
- **Una columna que puede quedar nula no protege una restricción de
  unicidad**: PostgreSQL considera distintos entre sí a dos nulos.
- **Ningún módulo escribe en `movimiento_caja` por su cuenta.** Todo pasa por
  `caja_service.registrar_movimiento()` (D-17).
- **No ordenar por `created_at` cuando el orden importa.** En PostgreSQL es la
  hora de inicio de la transacción y en SQLite tiene precisión de segundos
  (D-14).
- **Una venta guarda su propio precio y su propia descripción.** No cambiar
  eso por una referencia al catálogo (D-20).
- **Las reversiones de una anulación van a la caja abierta ahora**, nunca a la
  sesión original de la venta (D-23).
- **Las cuentas de plata del frontend van en centavos enteros.** No sumar
  pesos con decimales de JavaScript (D-24).
- **El arqueo ciego vive en la API, no en la pantalla.** Si algún endpoint
  empieza a devolver el efectivo esperado de una sesión abierta, el control se
  perdió aunque el frontend no lo muestre (D-12).

---

## 6. Nada roto

No hay tests en rojo, ni migraciones sin aplicar, ni funcionalidad a medias.
