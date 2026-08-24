# Anorak — sistema de gestión para local de ropa

Sistema de gestión para un local de ropa en Argentina. Facturación contra
ARCA (ex AFIP), moneda en pesos.

**El alcance de negocio se está redefiniendo** — ver "Estado del alcance" más
abajo.

## Stack — no se cambia

**Backend**: Python 3.12 · FastAPI · SQLAlchemy 2.0 async · Pydantic v2 ·
Alembic · PostgreSQL 16 (Supabase, **Session Pooler**) · JWT + bcrypt ·
WeasyPrint + Jinja2 · Cloudflare R2 (boto3).

**Frontend**: React 19 · Vite · TypeScript strict · Tailwind 4 · TanStack Query ·
react-router-dom · PWA con vite-plugin-pwa (Workbox) + Dexie para la cola offline.

**Infra**: backend en Railway, frontend en Cloudflare Pages, CI en GitHub Actions.

## Comandos

```bash
# Backend (desde backend/)
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload        # API en :8000
.venv/bin/pytest                               # tests (SQLite en memoria)
.venv/bin/ruff check app tests alembic         # lint
.venv/bin/black app tests alembic              # formato
.venv/bin/mypy app                             # tipos
.venv/bin/alembic revision --autogenerate -m "..."   # nueva migración
.venv/bin/alembic upgrade head                 # aplicarlas

# Frontend (desde frontend/)
pnpm install
pnpm dev            # :5173, con proxy de /api a :8000
pnpm test           # vitest
pnpm test:e2e       # playwright
pnpm exec tsc -b && pnpm exec eslint . && pnpm build
```

Después de generar una migración: `black` y `ruff check --fix` sobre
`alembic/`, o el CI la rechaza por formato.

## Reglas que no se negocian

Cada una viene de un error ya pagado. No se discuten, se aplican.

### Backend

| Regla | Por qué |
|---|---|
| `import bcrypt` directo, **nunca passlib** | passlib 1.7.4 lee `bcrypt.__about__.__version__`, que bcrypt 5.x no expone: falla al importar |
| `UUIDType` propio de `app/core/types.py`, nunca `UUID(as_uuid=True)` del dialecto postgresql | El tipo nativo rompe en SQLite, que es donde corren los tests |
| `FlexibleJSON` propio (`JSONB` con variante `sqlite`) | Mismo motivo |
| `enum_texto()` para columnas de enum, nunca `String` pelado con `Mapped[MiEnum]` | Con `String`, la fila leída de la base vuelve como `str` y cualquier `.value` explota en producción |
| Los servicios externos (ARCA, R2) se mockean con fixtures **automáticas** en `conftest.py` | Si hubiera que acordarse de pedirlas, el día que alguien escriba un test sin pedirla la suite sube archivos a un bucket real |
| `StrEnum`, nunca `(str, Enum)` | |
| Toda la plata en `Numeric`/`Decimal`. **Jamás float** | Un centavo mal redondeado en un cierre de caja es una hora de alguien buscándolo |
| Type hints en todas las funciones, docstring en las públicas | `mypy --strict` tiene que pasar |
| Los tests corren en **SQLite en memoria**, sin `.env` y sin red | ARCA, R2 y cualquier servicio externo se mockean con `pytest-mock` |
| **Nunca** definir una fixture `event_loop` en `conftest.py` | Está deprecada en pytest-asyncio moderno |
| `black` formatea, `ruff check` lintea. **Nunca `ruff format`** | Dos formateadores peleándose por los mismos archivos |
| La versión de `black` va clavada en `pyproject.toml` **y** en el rev del hook de pre-commit, iguales | Si difieren, el CI exige un formato distinto al que dejó el hook y se entra en un loop |

### Frontend

| Regla | Por qué |
|---|---|
| **Nunca** `localStorage` ni `sessionStorage`. El token vive en memoria (`lib/sesion.ts`) | Cualquier script de la página los lee |
| **Nunca** `any`. TypeScript en strict | |
| Toda fecha que se muestra va en **dd/mm/aaaa**, con los formateadores de `lib/fecha.ts` | |
| Para cargar fechas, `<CampoFecha>`; **nunca** `<input type="date">` | El nativo se dibuja con el formato del navegador, no con el del sitio |
| Los listados van con `<Listado>`, nunca una `<table>` suelta | Tabla en pantalla ancha y tarjetas en angosta, desde una sola definición de columnas |
| Ningún campo de carga por debajo de **16px** (`text-base`) | iOS amplía la pantalla solo al tocarlo |
| Los textos de ayuda viven **todos** en `lib/ayuda.ts`, nunca sueltos en una pantalla | El manual de usuario se arma de ahí: así las dos fuentes no se contradicen |
| Dos campos de una misma pantalla nunca llevan la misma etiqueta | "Motivo" y "Motivo" obligan a adivinar cuál es cuál, y un lector de pantalla los lee idénticos |

### Datos

- Cada tabla lleva `id` uuid PK, `created_at`, `updated_at`, `created_by`, `updated_by`.
- La auditoría **se escribe sola**: un listener de `before_flush` en
  `app/core/audit.py` registra cada INSERT/UPDATE/DELETE de cualquier tabla y
  completa los sellos de autoría. Ningún service registra cambios a mano.
- Bajas **lógicas** (`activo = false`), nunca físicas.
- Nunca commitear `.env`, `*.key`, `*.crt`, `*.pem`.

## Estado del alcance

El 24/08/2026 se retiraron todos los módulos de negocio (catálogo, precios,
stock y sucursales): el análisis del que salieron era equivocado. Hoy el
sistema tiene **ingreso, usuarios y auditoría**, y nada más.

El alcance nuevo está por definirse. Hasta que esté, no hay decisiones de
modelado de negocio vigentes: las que había están en el historial de git y
resumidas, con lo que se aprendió de cada una, en `docs/arquitectura.md` §6.

Lo que sí sigue vigente:

- El negocio es un local de ropa en Argentina: facturación contra ARCA, moneda
  en pesos, fechas en dd/mm/aaaa.
- El sistema se usa en el mostrador, desde computadora, tablet y celular.
- Los tres puestos son `ADMIN`, `ENCARGADO` y `VENDEDOR`.

## Errores ya resueltos — no repetirlos

| Problema | Solución |
|---|---|
| `created_by`/`updated_by` están en todas las tablas, así que una clave foránea a `usuario` arma un ciclo con cualquier tabla a la que `usuario` apunte, y la primera migración no puede ordenarse | Son UUID **sin** clave foránea. `audit_log.usuario_id` sí la tiene |
| `EmailStr` rechaza los dominios `.test` y `.local`: son nombres de uso reservado. La cuenta del seed quedaba creada pero no podía entrar nunca | Dominios reales en el seed y en los tests (`@anorak.com.ar`, `@prueba.com.ar`) |
| Una columna declarada `String` con anotación `Mapped[MiEnum]` devuelve `str` al leerla de la base. Los tests pasaban igual porque el objeto recién creado conserva el enum; el ingreso fallaba con 500 en producción | `enum_texto()` en `app/core/types.py`, con test de regresión en `tests/test_usuarios.py` |
| El registro de auditoría de un UPDATE puede quedar sin el valor anterior si la columna nunca se leyó de la base | Los endpoints traen la fila con `db.get()` antes de tocarla. Documentado en el docstring de `_diff` |
| Vitest levantaba los archivos de Playwright y fallaba con un error que no decía nada | `test.include` acotado a `src/` en `vite.config.ts` |
| Las migraciones se autogeneran contra SQLite | Funciona porque todos los tipos son portables, pero **hay que leer el archivo generado** antes de commitearlo |
| `client_admin` y `client_vendedor` eran el **mismo** cliente HTTP con el header pisado: un test que pedía los dos recibía el último resuelto, y los tests de permisos daban verde sin probar nada | Cada fixture de cliente abre el suyo (`_abrir_cliente` en `tests/conftest.py`) |
| Una columna que puede quedar nula dentro de una restricción de unicidad no la protege | PostgreSQL considera distintos entre sí a dos nulos. Si una columna forma parte de un índice único, no puede aceptar nulos |
| El `ultimo_ingreso` del login se guardaba de rebote, porque una consulta posterior disparaba el flush automático. Al sacar esa consulta dejó de escribirse | `await db.flush()` explícito en `login`. Un dato que se guarda o no según qué otra cosa pase después no puede quedar librado al azar |

## Documentación

- `docs/arquitectura.md` — el porqué de cada decisión y qué alternativa se
  descartó. Se actualiza cuando cambia una regla.
- `docs/handoff.md` — el estado real: qué se hizo, qué está roto, qué falta migrar.
- `CHANGELOG.md` — por módulo.
- `docs/manual/` — manual de usuario en MkDocs, escrito para quien atiende el
  local. Sin palabras de informática.
