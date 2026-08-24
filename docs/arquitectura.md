# Arquitectura — Anorak

Este archivo dice **por qué** el sistema es como es. El código ya dice qué
hace; lo que no se puede leer del código es qué alternativa se descartó y a
cambio de qué. Cuando una regla cambie, se actualiza el razonamiento acá, no
solo el código.

Última revisión: 24/08/2026.

> **Estado.** El 24/08/2026 se quitaron todos los módulos de negocio: el
> análisis del que salieron era equivocado. Quedan el ingreso al sistema, los
> usuarios, la auditoría automática y los componentes base. Lo que se sacó
> está en la sección 6, para que el análisis nuevo sepa qué se probó y por qué
> se hizo así. Nada de eso se perdió: está en el historial de git.

---

## 1. Qué es y para quién

Un sistema web para administrar un local de ropa en Argentina. El alcance
concreto se está redefiniendo; lo que sigue en pie es el contexto de uso, que
es lo que condiciona la arquitectura:

- Quien lo usa **atiende un mostrador**. Las operaciones tienen que resolverse
  rápido, con el cliente enfrente, muchas veces desde un celular.
- El negocio es en Argentina: la facturación es contra ARCA (ex AFIP) y la
  moneda es el peso.

---

## 2. Estilo general

Cliente-servidor con API REST, backend monolítico en capas y frontend SPA,
desplegados por separado.

Es deliberadamente conservador. Con un local, tres o cuatro personas usándolo
y sin nadie técnico en planta, microservicios o colas de mensajes serían un
costo permanente sin ningún beneficio. El monolito se despliega, se depura y
se respalda como una sola unidad.

La separación entre frontend y backend sí se justifica: permite que la
interfaz sea una PWA instalable —el mostrador tiene que poder seguir
funcionando con la conexión caída— y que cada parte se despliegue donde mejor
le queda: CDN para los estáticos, contenedor para la API.

---

## 3. Decisiones técnicas

Estas son las que sobrevivieron al cambio de análisis, porque ninguna depende
de qué se venda.

### D-1 · Los tests corren sobre SQLite en memoria

La suite corre en una máquina recién clonada: sin `.env`, sin Docker, sin
PostgreSQL, sin red. El costo es no poder usar tipos nativos de PostgreSQL en
los modelos, y por eso existen `UUIDType` y `FlexibleJSON` en
`app/core/types.py`.

El beneficio es que los tests corren en segundos y nadie tiene excusa para no
correrlos. Un test que necesita infraestructura es un test que no se corre.

Consecuencia: las migraciones se autogeneran contra SQLite. Funciona porque
todos los tipos son portables, pero **el archivo generado hay que leerlo**
antes de commitearlo.

### D-2 · La auditoría se escribe sola

Un único listener sobre `before_flush` (`app/core/audit.py`) registra cada
alta, cambio y baja de cualquier tabla, y completa `created_by`/`updated_by`.

**Alternativa descartada**: que cada service llame a un `registrar_cambio()`.
Alcanza con un endpoint nuevo escrito apurado para que un cambio quede sin
rastro, y eso se descubre el día que hace falta saber quién tocó qué. Lo que
depende de que alguien se acuerde, algún día no se hace.

Límite conocido y aceptado: si una columna nunca se leyó de la base y se le
asigna un valor, el valor anterior se pierde en el momento de la asignación
—ni `load_history()` lo recupera— y el registro queda con el "después" sin el
"antes". En la práctica no aparece, porque los endpoints traen la fila con
`db.get()` antes de tocarla, y eso carga todas las columnas.

### D-3 · `created_by`/`updated_by` no tienen clave foránea

Están en **todas** las tablas, así que cualquier tabla a la que `usuario`
apunte queda apuntándose de vuelta. Con la clave foránea puesta, eso es un
ciclo: PostgreSQL no puede ordenar la creación de las tablas y la primera
migración no corre. Ya pasó una vez.

Lo que se pierde es poco: las cuentas se dan de baja de forma lógica y nunca
se borran, así que un `created_by` apuntando a la nada no puede ocurrir.
`audit_log.usuario_id` sí conserva su clave foránea: esa tabla no participa
del ciclo.

### D-4 · El token de la sesión vive en memoria

Ni `localStorage` ni `sessionStorage`: cualquier script que corra en la página
los lee, y el token es la llave de todo el sistema.

El costo es real y está aceptado: al recargar la pestaña hay que volver a
entrar. Para un sistema que se usa con la pestaña abierta toda la jornada, es
barato. El manual lo explica, porque si no se explica se lee como una falla.

### D-5 · Un solo componente de listado para las tres pantallas

`<Listado>` se dibuja como tabla en pantalla ancha y como tarjetas en pantalla
angosta, desde una sola definición de columnas.

**Alternativa descartada**: mantener dos listados en paralelo. El que se usa
menos —siempre el de tarjetas— se olvida de mostrar la columna nueva, y nadie
lo nota hasta que alguien busca ese dato desde el celular.

Regla emparentada: ningún campo de carga por debajo de 16px. Por debajo de
eso, iPhone amplía la pantalla solo al tocarlo, y quien está cobrando tiene
que salir del zoom a mano en cada campo.

### D-6 · Las fechas, siempre en dd/mm/aaaa y con componente propio

Los formateadores viven en `lib/fecha.ts` y la carga se hace con
`<CampoFecha>`, nunca con `<input type="date">`: el control nativo lo dibuja
el navegador con el formato de la máquina, no con el del sitio. En una
computadora con Windows en inglés, la misma pantalla que **muestra**
05/03/2026 **pide** 03/05/2026. Nadie lo nota hasta que un movimiento queda
fechado dos meses después.

Detalle del que ya hay test: una fecha sola (`2026-03-05`) se arma en horario
local. Con `new Date('2026-03-05')`, JavaScript la lee como medianoche UTC y
en Argentina la muestra un día antes.

### D-7 · La ayuda en pantalla es la fuente del manual

Todos los textos de ayuda viven en `lib/ayuda.ts`, no sueltos dentro de cada
pantalla. Tres razones: se leen de una sola vez y hablan con una sola voz; el
dueño los puede corregir sin tocar el código de una pantalla; y el manual de
usuario se **arma** de ahí en lugar de reescribirse.

Si cada pantalla tuviera su texto suelto, el manual y el sistema se
contradirían el primer día que alguien cambie uno de los dos.

Regla al escribirlos: cuando el sistema **no deja** hacer algo, la ayuda dice
por qué. Un "no se puede" sin motivo se lee como que el sistema está roto, y
la persona termina llamando por teléfono en vez de resolverlo sola.

### D-8 · Los enum se guardan como texto, con conversión de ida y vuelta

`enum_texto()` en `app/core/types.py`. No es el tipo ENUM nativo de PostgreSQL
—sumar un estado no debe obligar a migrar un tipo, y además tiene que
funcionar en SQLite— pero tampoco es un `String` pelado.

La diferencia importa: con `String` y anotación `Mapped[MiEnum]`, el objeto
recién creado en Python conserva el enum y los tests pasan, pero la fila
leída de la base vuelve como `str` y cualquier `.value` explota. Se descubrió
probando el ingreso a mano, con la suite entera en verde.

### D-9 · Los identificadores se generan del lado del cliente

Toda tabla lleva `id` uuid como clave primaria, no un autoincremental
(`app/models/base.py::generate_uuid`).

El motivo viene del requisito de que el mostrador pueda vender sin conexión:
una operación registrada en el celular y sincronizada después necesita tener
su identificador desde el momento en que se crea. Un id que solo existe una
vez que el servidor contestó haría imposible ese circuito.

Ese requisito está en el pedido original y **no fue retractado**, pero
conviene confirmarlo con el análisis nuevo antes de construir sobre él. Lo que
sí es seguro es que el UUID no cuesta nada aunque el requisito cambie.

---

## 4. Cómo se construye: en rodajas verticales

No se hace el modelo completo de todos los módulos y después las pantallas. Se
hace de punta a punta, tanda por tanda, y cada tanda deja el sistema
funcionando.

Los tests quedan en verde en cada tanda. Si algo queda rojo es una regresión,
no ruido de fondo, y no se avanza con el CI roto.

| # | Tanda | Estado |
|---|---|---|
| 1 | Base: repo, CI, ingreso con roles, marco de pantallas, auditoría automática, migraciones | **Hecha** |
| 2+ | A definir con el análisis nuevo | Pendiente |

---

## 5. Endurecimiento operativo

Medidas que ya están puestas, heredadas de incidentes reales en otro sistema
con el mismo stack:

| Medida | Problema que evita |
|---|---|
| `lock_timeout = 10s` | Una escritura que no consigue el lock falla con error en vez de colgarse |
| `idle_in_transaction_session_timeout = 60s` | PostgreSQL cierra conexiones huérfanas dentro de una transacción y libera sus locks |
| `pool_pre_ping` | Conexiones muertas por el pooler se detectan antes de usarse |
| Las migraciones corren en el arranque (`Procfile`) | Desplegar sin migrar deja el backend contra una base vieja |
| `schema_check` avisa si la base no está al día | Loguea fuerte pero no frena el arranque: si el backend no levanta, el local no vende |

Los dos timeouts se aplican con un `SET` explícito en el evento `connect` y no
en `connect_args`, porque el Session Pooler de Supabase descarta los
`server_settings` del startup packet.

Sobre Supabase: en producción va la URL del **Session Pooler** (puerto 6543).
La URL directa resuelve solo a IPv6 y Railway sale por IPv4: falla con
"Network is unreachable".

---

## 6. Lo que se quitó el 24/08/2026, y qué se aprendió

Se construyeron y se retiraron tres módulos —catálogo, precios y stock— más
las sucursales. El código está en el historial de git (commits `Tanda 2` y
`Tanda 3`). Esto queda anotado para que el análisis nuevo no vuelva a chocar
con lo mismo:

| Se quitó | Lo que costó descubrir, y sigue valiendo |
|---|---|
| Producto → Variante → Stock | Si el stock cuelga del producto, el sistema no puede contestar "¿la tenés en M?", y meter la variante después obliga a inventar a qué variante correspondió cada movimiento histórico |
| Catálogo cerrado de talles y colores | Con texto libre conviven "M" y "m" como cosas distintas, y el stock de la misma prenda queda partido en dos |
| Curva de talles obligatoria por categoría | Dejar el talle nulo para lo que no tiene talle rompe la restricción de unicidad: PostgreSQL considera distintos entre sí a dos nulos |
| Precio con `vigente_desde`/`vigente_hasta` | Un precio es un **estado**: hay exactamente una fila vigente, garantizada por un índice único parcial. Copiarlo a la fila del producto solo agrega algo que se desincroniza |
| Stock con saldo **y** movimientos | Un saldo es una **cuenta**: conviene guardarla y poder rehacerla sumando los movimientos, porque si los dos números difieren hay un bug y tiene que notarse |
| Un solo punto de escritura del stock | Con cada módulo actualizando el saldo por su cuenta, alcanza con que uno se olvide del movimiento para que el número quede sin explicación |
| `with_for_update()` sobre la fila de saldo | Dos cajas vendiendo la última unidad leen 1 las dos y restan las dos. SQLAlchemy omite el `FOR UPDATE` en SQLite, así que el bloqueo no rompe los tests |
| Sucursales desde el día uno | La idea era no tener que inventar después a qué local perteneció cada movimiento histórico. Si el análisis nuevo vuelve a necesitar más de un punto físico, conviene ponerlo antes de que haya datos |

Estas observaciones son sobre **cómo modelar**, no sobre **qué modelar**. Lo
segundo es lo que quedó sin efecto.
