# Estado del sistema

Qué está hecho, qué está a medias y qué falta. Este archivo se actualiza al
cerrar cada tanda, y dice la verdad aunque sea incómoda: un "listo" que no lo
está cuesta más caro que un pendiente anotado.

**Última actualización**: 20/08/2026 — cierre de la tanda 1.

---

## 1. Resumen

| | |
|---|---|
| Tanda actual | 1 (base) — **cerrada** |
| Próxima | 2 (catálogo: productos, variantes, categorías, marcas, precios) |
| Tests backend | 36, todos en verde |
| Tests frontend | 10 unitarios + 3 de punta a punta |
| Migraciones | 1, aplicada. Sin pendientes |
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

Probado a mano de punta a punta el 20/08/2026: ingreso con la cuenta del seed,
listado y alta de sucursal, y lectura del registro de auditoría distinguiendo
lo que escribió el sistema (sin usuario) de lo que escribió una persona.

### Frontend

- **Ingreso** con el token en memoria. Al recargar la pestaña hay que volver a
  entrar, y la ayuda de la pantalla lo explica.
- **Marco general**: menú filtrado por puesto, columna a la izquierda en
  pantalla ancha y fila deslizable en el celular.
- **Pantallas**: Inicio, Sucursales y Usuarios (las dos últimas, solo admin).
- **Componentes base**: `<Listado>` (tabla en pantalla ancha, tarjetas en
  angosta, desde una sola definición de columnas), `<CampoFecha>` (dd/mm/aaaa,
  sin `<input type="date">`), `<Campo>`, `<Selector>`, `<Boton>`, `<Ayuda>`.
- **Bibliotecas propias**: `lib/fecha.ts`, `lib/dinero.ts`, `lib/api.ts`,
  `lib/sesion.ts`, `lib/ayuda.ts`.
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

---

## 5. Nada roto

No hay tests en rojo, ni migraciones sin aplicar, ni funcionalidad a medias
dentro de la tanda 1.
