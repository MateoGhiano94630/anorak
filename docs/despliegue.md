# Cómo desplegar el sistema

Paso a paso, desde una máquina donde el proyecto todavía es local hasta el
local usándolo.

Son cuatro piezas y se arman en este orden, porque cada una necesita algo de
la anterior:

```
GitHub  →  Supabase  →  Railway        →  Cloudflare Pages
(código)   (la base)    (la API)           (las pantallas)
```

Calculá **una hora** la primera vez. Los despliegues siguientes son un `git
push`.

> Antes de empezar necesitás cuenta en GitHub, Supabase, Railway y Cloudflare.
> Las cuatro tienen plan gratuito suficiente para arrancar.

---

## 1. Subir el código a GitHub

Hoy el repositorio existe solo en tu máquina, así que el CI nunca corrió y ni
Railway ni Cloudflare tienen de dónde leerlo.

Creá un repositorio **privado** en GitHub —el proyecto va a tener datos y
claves del negocio— y desde la carpeta del proyecto:

```bash
git remote add origin git@github.com:TU-USUARIO/anorak.git
git push -u origin main
```

Andá a la pestaña **Actions** del repositorio y esperá a que el CI termine en
verde. Si algo falla, arreglalo antes de seguir: desplegar código que no pasa
sus propias pruebas es empezar con una deuda.

---

## 2. La base de datos en Supabase

1. Creá un proyecto nuevo. Elegí la región **South America (São Paulo)**: es
   la más cercana y la latencia se nota en el mostrador.
2. Guardá la contraseña de la base que te muestra al crearlo. **No se puede
   volver a ver**; si la perdés hay que resetearla.
3. Entrá a **Project Settings → Database → Connection string** y buscá la
   sección **Connection pooling**.

### Cuál de las tres direcciones usar

Supabase te ofrece tres, y elegir mal es el error más común:

| Cuál | Cómo se ve | Sirve |
|---|---|---|
| Conexión directa | `db.<ref>.supabase.co:5432` | **No.** Resuelve solo a IPv6 y Railway sale por IPv4: falla con "Network is unreachable" |
| **Session pooler** | `aws-0-<región>.pooler.supabase.com:5432` | **Sí. Es la que va.** |
| Transaction pooler | `aws-0-<región>.pooler.supabase.com:6543` | Anda, pero rompe las consultas preparadas de asyncpg salvo que se desactive el caché a mano |

Copiá la del **session pooler** y adaptala así:

```
postgresql+asyncpg://postgres.<ref>:<CONTRASEÑA>@aws-0-<región>.pooler.supabase.com:5432/postgres
```

Dos detalles que hacen fallar el arranque y no son obvios:

- El prefijo tiene que ser **`postgresql+asyncpg://`**, no `postgresql://`. El
  sistema usa un driver asincrónico y con el prefijo corto ni siquiera lo carga.
- Si la contraseña tiene `@`, `#`, `/` o `:`, hay que **escaparlos**. Una `@`
  sin escapar hace que la dirección se parta en el lugar equivocado y el error
  que ves habla de un host que no existe. La forma rápida de escaparla:

  ```bash
  python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" 'tu contraseña'
  ```

No hace falta crear ninguna tabla a mano: las migraciones corren solas cuando
arranca el backend (paso 3).

---

## 3. El backend en Railway

1. **New Project → Deploy from GitHub repo** y elegí el repositorio.
2. En **Settings → Root Directory** poné `backend`. Sin eso, Railway busca en
   la raíz del repositorio y no encuentra el proyecto de Python.
3. En **Settings → Networking** tocá **Generate Domain**. Te va a quedar algo
   como `anorak-production.up.railway.app`. **Anotalo**: lo necesitás en el
   paso 4.

### Las variables de entorno

En la pestaña **Variables**, cargá estas:

| Variable | Qué poner | Si no la ponés |
|---|---|---|
| `DATABASE_URL` | La dirección del paso 2 | Escribe en un archivo SQLite del contenedor, que se borra en cada despliegue. **Perdés todo** |
| `JWT_SECRET_KEY` | Una clave larga al azar | Queda la de fábrica, que está en el código. Cualquiera que vea el repositorio puede fabricarse una sesión de administrador |
| `SEED_PASSWORD` | Una contraseña para el primer ingreso | Queda `anorak1234`, que también está en el código |
| `ENVIRONMENT` | `production` | Con `development` el sistema escribe **cada consulta SQL** en los logs: se vuelven ilegibles y consumen la cuota |
| `FRONTEND_URL` | Se completa en el paso 5 | El navegador bloquea las llamadas del frontend a la API |
| `FONDO_FIJO_SUGERIDO` | El fondo del cajón, por ejemplo `20000.00` | Usa 20000.00 |

Para generar la clave del token:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Dejá `FRONTEND_URL` con cualquier valor por ahora; se corrige en el paso 5.

### Qué pasa al desplegar

Railway lee `backend/nixpacks.toml`, instala Python 3.12 y las bibliotecas que
necesita WeasyPrint, y arranca con:

```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Las migraciones **corren solas antes de levantar la API**. En este primer
despliegue son las que crean todas las tablas.

Al arrancar, el sistema también crea la cuenta `admin@anorak.com.ar` con la
contraseña de `SEED_PASSWORD`, y los cinco medios de pago.

### Comprobar que quedó bien

```bash
curl https://TU-BACKEND.up.railway.app/health
```

Tiene que contestar `{"estado":"ok","version":"0.1.0"}`.

Si no contesta, mirá los logs en Railway. Los errores más comunes están en la
sección **Problemas conocidos**, al final.

---

## 4. El frontend en Cloudflare Pages

1. **Workers & Pages → Create → Pages → Connect to Git** y elegí el
   repositorio.
2. Configuración de la compilación:

   | Campo | Valor |
   |---|---|
   | Root directory | `frontend` |
   | Build command | `pnpm install --frozen-lockfile && pnpm build` |
   | Build output directory | `dist` |

3. En **Environment variables**, para el entorno de **Production**:

   | Variable | Valor |
   |---|---|
   | `VITE_API_URL` | `https://TU-BACKEND.up.railway.app` (el dominio del paso 3, **sin barra al final**) |
   | `NODE_VERSION` | `22` |

> **`VITE_API_URL` se usa al compilar, no al ejecutar.** Queda escrita dentro
> del JavaScript que se genera. Si después cambiás el dominio del backend, no
> alcanza con cambiar la variable: hay que **volver a compilar** desde
> Cloudflare (*Deployments → Retry deployment*).

Cuando termine te va a dar una dirección como
`anorak.pages.dev`. **Anotala**: la necesitás en el paso 5.

El archivo `frontend/public/_redirects` ya está en el repositorio y hace que
entrar directo a `/ventas` o recargar esa pantalla funcione. Sin él,
Cloudflare devolvería 404 porque ese archivo no existe: la ruta la resuelve el
navegador.

---

## 5. Conectar los dos

Volvé a Railway y poné en `FRONTEND_URL` la dirección exacta del paso 4:

```
FRONTEND_URL=https://anorak.pages.dev
```

**Sin barra al final y con `https://` adelante.** El navegador compara ese
texto carácter por carácter contra el origen de la página; una barra de más y
bloquea todas las llamadas.

Railway reinicia solo al guardar la variable.

---

## 6. El primer ingreso

1. Entrá a `https://anorak.pages.dev`.
2. Ingresá con `admin@anorak.com.ar` y la contraseña de `SEED_PASSWORD`.
3. **Cambiala inmediatamente**, desde tu propia cuenta.
4. Creá las cuentas de quienes van a usar el sistema, en **Usuarios**.

La cuenta `admin@anorak.com.ar` no se puede borrar —las cuentas se dan de baja,
no se eliminan, porque su nombre queda en las operaciones que hicieron—, pero
sí conviene dejarla con una contraseña que solo vos sepas.

---

## 7. Comprobar que anda de verdad

Un `/health` en verde solo dice que el proceso arrancó. Esto prueba el
circuito completo, y son cinco minutos:

1. Entrá con tu usuario.
2. **Caja → Abrir la caja** con el fondo que haya en el cajón.
3. **Catálogo →** cargá un artículo cualquiera con su precio.
4. **Vender →** agregalo, cobralo en efectivo, registrá la venta.
5. **Caja →** tiene que aparecer el cobro con el número de la venta.
6. **Ventas →** abrí la venta y anulala con un motivo.
7. **Caja →** tiene que aparecer la devolución, y el cajón volver al fondo.
8. **Caja → Cerrar la caja**, contá el efectivo y cerrá.

Si los ocho pasos salen, el sistema está funcionando de punta a punta: la base
guarda, la API responde, el navegador llega y los números cuadran.

---

## 8. Cada despliegue siguiente

```bash
git push
```

Y nada más. Railway y Cloudflare escuchan la rama `main` y despliegan solos.
Las migraciones nuevas se aplican en el arranque del backend.

Tres cosas para tener presentes:

- **Mirá que el CI esté en verde** antes de que el despliegue termine. Si el
  CI falla, ese código igual se desplegó: Railway y Cloudflare no esperan a
  GitHub Actions.
- **Los dos se despliegan por separado y no al mismo tiempo.** Si un cambio
  toca la API y las pantallas a la vez, hay unos segundos en los que una
  versión nueva del frontend le habla a una vieja de la API. Con el sistema en
  un solo local es tolerable; el día que moleste, se resuelve desplegando
  primero el backend.
- **Una migración que borra o renombra una columna no se puede revertir con un
  despliegue.** Antes de subir una de esas, sacá un respaldo desde Supabase.

---

## 9. Problemas conocidos y cómo se ven

| Lo que ves | Qué pasa |
|---|---|
| El backend arranca y muere enseguida, con "Network is unreachable" en los logs | `DATABASE_URL` apunta a la conexión directa de Supabase, que es solo IPv6. Usá la del **session pooler** (paso 2) |
| "Can't load plugin: sqlalchemy.dialects:postgresql.asyncpg" o similar | Al `DATABASE_URL` le falta el `+asyncpg` |
| El backend arranca pero los datos desaparecen en cada despliegue | Falta `DATABASE_URL`: está usando el SQLite del contenedor, que se borra |
| La pantalla de ingreso carga pero al entrar no pasa nada | Es CORS. `FRONTEND_URL` en Railway no coincide **exactamente** con la dirección de la página. Miralo en la consola del navegador: el error lo dice |
| Todo anda pero el frontend le pega a `/api` y da 404 | Falta `VITE_API_URL` en Cloudflare, o se agregó después de compilar. Volvé a compilar |
| Cambié el dominio del backend y el frontend sigue yendo al viejo | `VITE_API_URL` quedó escrita en el JavaScript compilado. *Retry deployment* en Cloudflare |
| Los logs de Railway están llenos de consultas SQL | Falta `ENVIRONMENT=production` |
| "La base está en la revisión X y el código espera Y" en los logs | Una migración no se aplicó. El sistema arranca igual a propósito —si el backend no levanta, el local no vende— pero hay que resolverlo |

### Una limitación conocida

`FRONTEND_URL` acepta **una sola dirección**. Cloudflare Pages genera además
una dirección distinta por cada rama y por cada vista previa, y esas no van a
poder hablar con la API.

Para el uso normal no molesta. Si algún día hace falta probar una vista previa
contra la API real, hay que cambiar la configuración para que acepte una lista
de direcciones.

---

## 10. Lista de control

Antes de darle el sistema a alguien del local:

- [ ] El CI está en verde en GitHub
- [ ] `DATABASE_URL` apunta al session pooler de Supabase, con `+asyncpg`
- [ ] `JWT_SECRET_KEY` **no** es la de fábrica
- [ ] `SEED_PASSWORD` **no** es la de fábrica
- [ ] `ENVIRONMENT` es `production`
- [ ] `FRONTEND_URL` es la dirección exacta de Cloudflare, sin barra final
- [ ] `VITE_API_URL` es la dirección exacta de Railway, sin barra final
- [ ] La contraseña de `admin@anorak.com.ar` se cambió después del primer ingreso
- [ ] Las cuentas de quienes atienden están creadas, cada una con su puesto
- [ ] Los medios de pago tienen cargada su comisión y sus días de acreditación
- [ ] El circuito del paso 7 salió completo
- [ ] Los respaldos automáticos de Supabase están activos, y probaste
      restaurar uno

El último punto es el que más se saltea y el único que no se puede improvisar
el día que hace falta.
