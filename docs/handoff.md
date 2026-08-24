# Estado del sistema

Qué está hecho, qué está a medias y qué falta. Este archivo se actualiza al
cerrar cada tanda, y dice la verdad aunque sea incómoda: un "listo" que no lo
está cuesta más caro que un pendiente anotado.

**Última actualización**: 24/08/2026 — limpieza de los módulos de negocio.

---

## 1. Resumen

| | |
|---|---|
| Estado | Base funcionando. Alcance de negocio **por definir** |
| Última tanda cerrada | 1 (base: ingreso, usuarios, auditoría) |
| Próxima | A definir con el análisis nuevo |
| Tests backend | 31, todos en verde |
| Tests frontend | 13 unitarios + 3 de punta a punta (por 2 dispositivos) |
| Migraciones | 1, aplicada. Sin pendientes |
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

### Frontend

- **Ingreso** con el token en memoria. Al recargar la pestaña hay que volver a
  entrar, y la ayuda de la pantalla lo explica.
- **Marco general**: menú filtrado por puesto, columna a la izquierda en
  pantalla ancha y fila deslizable en el celular.
- **Pantallas**: Inicio y Usuarios.
- **Componentes base**: `<Listado>` (tabla en pantalla ancha, tarjetas en
  angosta, desde una sola definición de columnas), `<CampoFecha>` (dd/mm/aaaa,
  sin `<input type="date">`), `<Campo>`, `<Selector>`, `<Boton>`, `<Ayuda>`.
- **Bibliotecas propias**: `lib/fecha.ts`, `lib/dinero.ts`, `lib/api.ts`,
  `lib/sesion.ts`, `lib/ayuda.ts`, `lib/etiquetas.ts`, `lib/tipos.ts`.

Probado a mano el 24/08/2026, después de la limpieza: ingreso con la cuenta
del seed, alta de usuario desde la API, y lectura del registro de auditoría
distinguiendo lo que escribió el sistema (sin usuario) de lo que escribió una
persona.

---

## 4. Qué falta y hay que tener en cuenta

| # | Pendiente | Cuándo |
|---|---|---|
| P-1 | **El alcance de negocio está sin definir.** Es lo que bloquea todo lo demás | Antes de la próxima tanda |
| P-2 | El repositorio es local: no hay remoto en GitHub, así que el CI nunca corrió | Antes de la próxima tanda |
| P-3 | Nada está desplegado. Falta crear el proyecto en Railway (con la URL del Session Pooler de Supabase) y en Cloudflare Pages | Cuando haya algo que mostrar |
| P-4 | `pre-commit install` no se corrió en la máquina de desarrollo | Antes del primer commit compartido |
| P-5 | El manual de usuario tiene las páginas de ingreso y usuarios. Falta publicarlo | Va creciendo con cada tanda |
| P-6 | La facturación está apagada (`ARCA_HABILITADO=false`) y sin certificados | Cuando el dueño los tenga |
| P-7 | Los tests de punta a punta del CI no levantan el backend, así que prueban el frontend solo | Evaluar un trabajo de CI que levante los dos |
| P-8 | La configuración de ARCA y R2 quedó declarada pero sin consumidor. `boto3`, `weasyprint`, `pillow` y `qrcode` siguen en las dependencias porque son parte del stack elegido | Se usan cuando vuelva a haber un módulo que los necesite |

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

---

## 6. Nada roto

No hay tests en rojo, ni migraciones sin aplicar, ni funcionalidad a medias.
