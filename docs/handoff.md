# Estado del sistema

Qué está hecho, qué está a medias y qué falta. Este archivo se actualiza al
cerrar cada tanda, y dice la verdad aunque sea incómoda: un "listo" que no lo
está cuesta más caro que un pendiente anotado.

**Última actualización**: 23/08/2026 — cierre de la tanda 3.

---

## 1. Resumen

| | |
|---|---|
| Tanda actual | 3 (stock) — **cerrada** |
| Próxima | 4 (POS: venta, medios de pago, caja abierta/cerrada, ticket en PDF) |
| Tests backend | 103, todos en verde |
| Tests frontend | 22 unitarios + 3 de punta a punta (por 2 dispositivos) |
| Migraciones | 3, aplicadas. Sin pendientes |
| CI | Escrito y completo. **Todavía no corrió en GitHub**: el repositorio es local |
| Despliegue | **No desplegado.** Ni Railway ni Cloudflare Pages están configurados |

---

## 2. Qué quedó funcionando

### Backend

- **Ingreso con JWT y bcrypt directo.** `POST /auth/login`, `GET /auth/me`,
  `POST /auth/cambiar-password`. Cada ingreso deja registrada la fecha.
- **Tres roles**: `ADMIN`, `ENCARGADO`, `VENDEDOR`. El admin es superset de
  todos los permisos y no hace falta nombrarlo en cada ruta.
- **Sucursales**: alta, listado y modificación. Depósito es una sucursal con
  `tipo = DEPOSITO`. El código se normaliza a mayúsculas y es único.
- **Usuarios**: alta, listado, modificación. Baja lógica. Un admin no se puede
  dar de baja a sí mismo. El hash de contraseña no sale nunca por la API.
- **Auditoría automática**: un listener sobre `before_flush` registra cada
  alta, cambio y baja de cualquier tabla y completa `created_by`/`updated_by`.
  Se lee por `GET /audit-log`, solo admin, con filtros por tabla, registro y
  operación. Es de solo lectura: no hay endpoint para modificarla ni borrarla.
- **Seed idempotente** al arrancar: crea la sucursal `PRIN` ("Local principal")
  y la cuenta `admin@anorak.com.ar` con `SEED_PASSWORD`. Si la contraseña
  sigue siendo la de fábrica, el arranque avisa por log.
- **Chequeo de esquema** al arrancar: compara la revisión de la base contra el
  head del código y loguea ERROR si difieren, sin frenar el arranque.

Probado a mano de punta a punta el 20/08/2026, dos veces:

1. Contra la API: ingreso con la cuenta del seed, alta de sucursal, y lectura
   del registro de auditoría distinguiendo lo que escribió el sistema (sin
   usuario) de lo que escribió una persona.
2. En un navegador real, con el frontend contra la API: ingreso, alta de curva
   de talles, categoría, marca y color; alta de una prenda; generación de sus
   combinaciones; carga del precio; y verificación de que el catálogo la
   muestra con el importe bien formateado. Sin errores en la consola.
3. En un navegador real (23/08/2026): carga de mercadería por código,
   corrección por conteo con el panel actualizándose sin recargar, mínimo y
   filtro de reposición, y el historial mostrando los dos movimientos con su
   signo y cuánto quedó. Sin errores en la consola.

### Backend — catálogo (tanda 2)

- **Curvas de talle** con sus talles ordenados, **categorías** (cada una con su
  curva), **marcas** y **colores** con su tono.
- **Productos** con categoría, marca, género y temporada; búsqueda por texto y
  filtro por categoría y marca.
- **Generación de variantes**: se eligen talles y colores y se crean todas las
  combinaciones. Las que ya existen se saltean, así sumar un color es volver a
  ejecutarlo. Un talle que no pertenece a la curva de la categoría se rechaza.
- **Código interno automático** por variante, legible y único, y código de
  barras opcional del proveedor. Búsqueda por cualquiera de los dos.
- **Precios con vigencia**: cambiar uno cierra el anterior. Un índice único
  parcial impide dos precios vigentes para la misma variante. Cambio masivo
  por producto y consulta del historial.
- **Imágenes** en Cloudflare R2, con dirección firmada al servir. Nunca se
  contacta R2 en los tests.

### Backend — stock (tanda 3)

- **Existencias por variante y sucursal.** La fila nace con el primer
  movimiento, no al dar de alta la prenda.
- **Un solo punto de escritura**: `stock_service.registrar_movimiento()`. Toma
  la fila con `with_for_update()` para que dos cajas no vendan la misma última
  unidad.
- **Movimientos inmutables** con tipo, cantidad con signo, cuánto quedó,
  motivo, y el documento que los originó cuando lo hay. Sin endpoint de
  borrado, con un test que lo comprueba.
- **Ingresos y ajustes** desde la pantalla; el resto de los tipos los va a
  generar el módulo que corresponda (venta, devolución, transferencia).
- **Alertas de mínimo** por prenda y sucursal.
- **Control de consistencia** (`GET /stock/control`, solo admin): compara el
  saldo contra la suma de movimientos. Tiene que devolver siempre vacío.
- Vender sin existencias se rechaza con `StockInsuficienteError`; el ajuste a
  la baja nunca se rechaza.

### Frontend

- **Ingreso** con el token en memoria. Al recargar la pestaña hay que volver a
  entrar, y la ayuda de la pantalla lo explica.
- **Marco general**: menú filtrado por puesto, columna a la izquierda en
  pantalla ancha y fila deslizable en el celular.
- **Pantallas**: Inicio, Sucursales y Usuarios (las dos últimas, solo admin).
- **Componentes base**: `<Listado>` (tabla en pantalla ancha, tarjetas en
  angosta, desde una sola definición de columnas), `<CampoFecha>` (dd/mm/aaaa,
  sin `<input type="date">`), `<Campo>`, `<Selector>`, `<Boton>`, `<Ayuda>`.
- **Pantallas de catálogo**: listado con buscador, filtro y rango de precios;
  detalle de la prenda con generación de talles y colores, precios, historial y
  fotos; y la pantalla de marcas, colores, categorías y curvas de talle.
- **Pantallas de existencias**: listado con buscador, filtro por local y por
  "lo que hay que reponer"; panel por prenda para cargar, corregir y fijar el
  mínimo; carga de mercadería por código; e historial de movimientos.
- **Bibliotecas propias**: `lib/fecha.ts`, `lib/dinero.ts`, `lib/api.ts`,
  `lib/sesion.ts`, `lib/ayuda.ts`, `lib/etiquetas.ts`, `lib/catalogos.ts`,
  `lib/stock.ts`.
- **PWA**: manifest y service worker generados en el build. La cola offline
  (Dexie) **no está escrita todavía** — va con la tanda del punto de venta.

---

## 3. Qué falta y hay que tener en cuenta

| # | Pendiente | Cuándo |
|---|---|---|
| P-1 | El repositorio es local: no hay remoto en GitHub, así que el CI nunca corrió | Antes de la tanda 2 |
| P-2 | Nada está desplegado. Falta crear el proyecto en Railway (con la URL del Session Pooler de Supabase) y en Cloudflare Pages | Cuando haya algo que mostrar |
| P-3 | `pre-commit install` no se corrió en la máquina de desarrollo | Antes del primer commit compartido |
| P-4 | El manual de usuario tiene la estructura y las páginas de la tanda 1. Falta publicarlo | Va creciendo con cada tanda |
| P-5 | La cola offline del punto de venta (Dexie) está decidida y documentada, pero no escrita | Tanda 4 |
| P-6 | La facturación está apagada (`ARCA_HABILITADO=false`) y sin certificados | Cuando el dueño los tenga |
| P-7 | R2 no tiene credenciales cargadas. Las fotos se pueden subir solo cuando estén: sin ellas, la subida contesta 503 con un mensaje claro y el catálogo funciona igual sin imágenes | Cuando el dueño abra la cuenta de Cloudflare |
| P-8 | Los tests de punta a punta del CI no levantan el backend, así que prueban el frontend solo. El circuito completo se verificó a mano | Evaluar un trabajo de CI que levante los dos, en una tanda próxima |

## 4. Cosas que hay que saber antes de tocar algo

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
- **`created_by`/`updated_by` no tienen clave foránea**, a propósito. Ver D-11
  en `docs/arquitectura.md`.
- **Vender sin stock está bloqueado** por decisión del dueño, pero detrás de
  `PERMITIR_STOCK_NEGATIVO`. Si alguna vez hay que cambiarlo, es una variable
  de entorno.
- **Cada fixture de cliente HTTP abre el suyo.** No volver a la versión que
  compartía uno solo cambiándole el header: un test que pide `client_admin` y
  `client_vendedor` a la vez recibiría el mismo objeto, y los tests de permisos
  darían verde sin probar nada.
- **Una categoría siempre tiene curva de talles**, incluso para lo que no tiene
  talle (curva "Único"). No hacer que `talle_id` acepte nulos: la restricción
  de unicidad de variantes dejaría de funcionar (D-18).
- **El precio vigente es la fila con `vigente_hasta` nulo.** No agregar una
  columna de precio actual en `variante`: sería una segunda versión del mismo
  dato (D-19).
- **Ningún módulo toca `stock.cantidad`.** Todo pasa por
  `stock_service.registrar_movimiento()` (D-23). El día que `GET /stock/control`
  devuelva algo, es que alguien rompió esta regla.
- **Un mínimo en cero no alerta.** No sacar esa condición: sin ella, toda
  prenda agotada del catálogo aparecería en las alertas (D-25).

---

## 5. Nada roto

No hay tests en rojo, ni migraciones sin aplicar, ni funcionalidad a medias
dentro de las tandas 1, 2 y 3.
