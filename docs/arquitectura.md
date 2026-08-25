# Arquitectura — Anorak

Este archivo dice **por qué** el sistema es como es. El código ya dice qué
hace; lo que no se puede leer del código es qué alternativa se descartó y a
cambio de qué. Cuando una regla cambie, se actualiza el razonamiento acá, no
solo el código.

Última revisión: 24/08/2026 (módulo de ventas).

> **Estado.** El 24/08/2026 se quitaron todos los módulos de negocio que
> venían de un análisis equivocado, y el mismo día se empezó de nuevo por la
> **caja**. Lo que se sacó está en la sección 7, para que no se vuelva a
> chocar con lo mismo. Nada se perdió: está en el historial de git.

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

## 4. La caja

La caja es el primer módulo de negocio del sistema. Es el contenedor: una
**sesión** va desde que alguien la abre hasta que la cierra, y todo lo demás
—los cobros, los retiros, los gastos y el arqueo— cuelga de ella.

Hoy no cobra ventas, porque el punto de venta todavía no existe. Hasta
entonces funciona como un libro de caja, que ya es usable tal cual. El gancho
por donde va a entrar el cobro de una venta está puesto: `movimiento_caja`
tiene un par de columnas que apuntan al documento que lo originó, sin clave
foránea porque apuntan a tablas distintas según el tipo.

### D-10 · La sesión de caja es del puesto, no de la persona

Hay una sesión por jornada: la abre quien llega primero y cobran todos sobre
el mismo cajón. Es lo que refleja un mostrador con un solo cajón compartido.

**Lo que se resigna, y está aceptado**: una diferencia de arqueo no tiene
dueño, porque durante el día cobraron varios. Lo que sí queda atribuido es
cada movimiento individual —quién hizo cada retiro, cada gasto— más quién
abrió y quién cerró. Alcanza para investigar una diferencia; no para
adjudicarla sola.

**Alternativa descartada**: una sesión por vendedor. Solo tiene sentido si
cada uno tiene su propio cajón; si comparten uno, dos sesiones abiertas sobre
la misma plata dan dos arqueos que no pueden cerrar los dos.

### D-11 · El arqueo se congela al cerrar

`efectivo_declarado`, `efectivo_esperado` y `diferencia` se guardan como
columnas y no se recalculan nunca.

Un arqueo es un documento: dice qué se contó y qué creía el sistema **en ese
momento**. Si el esperado se recalculara, cualquier corrección posterior
cambiaría la historia y la diferencia dejaría de coincidir con la que la
persona vio al cerrar.

Es el mismo criterio que hace que una línea de venta guarde el precio con el
que se vendió, y el opuesto al del saldo de una cuenta, que sí conviene poder
rehacer.

### D-12 · El arqueo es a ciegas

Mientras la caja está abierta, la API **no informa** el efectivo esperado: no
viene en la sesión, no aparece en los totales por medio de pago, y ni siquiera
el error de "no hay tanto efectivo" dice cuánto hay. Recién al declarar lo
contado, el cierre revela el esperado y la diferencia.

Si el sistema mostrara el número antes, la tentación es tipearlo y el arqueo
deja de medir nada.

**El límite, dicho de frente**: los movimientos del día sí se ven, con sus
importes, así que quien quiera sumarlos puede. Esconderlos también volvería la
pantalla inútil para trabajar. Esto es **fricción, no un candado**: sirve para
que el número no se copie por inercia, no para impedir que alguien decidido lo
calcule.

### D-13 · La diferencia del arqueo se anota como movimiento

Al cerrar, si lo contado no coincide, la diferencia entra como un movimiento
más antes del retiro final.

Sin eso, el libro quedaría diciendo una cosa y el cajón otra: la suma de los
movimientos daría el esperado y en el cajón habría lo contado. Con la
diferencia anotada, al terminar el cierre **la suma de los movimientos en
efectivo es exactamente el fondo que quedó**. Es un invariante comprobable, y
hay un test que lo comprueba.

### D-14 · Los movimientos llevan número de renglón propio

`movimiento_caja.numero` es 1, 2, 3 dentro de la sesión, con índice único.

No se ordenan por `created_at` porque ese orden es indeterminado en los dos
motores: en SQLite `CURRENT_TIMESTAMP` tiene precisión de segundos, y en
PostgreSQL devuelve la hora de **inicio de la transacción**, así que todo lo
escrito en el mismo flush queda con el mismo valor. Un libro de caja se lee en
orden; el orden no puede depender de eso.

La restricción de unicidad es la red: si dos personas cargan un movimiento en
el mismo instante sobre la misma caja, la segunda falla en vez de quedar con
un renglón repetido y un orden inventado.

### D-15 · El fondo fijo queda en el cajón

Al cerrar se retira lo que sobra de un fondo fijo, y ese retiro se anota como
movimiento. Así la apertura del día siguiente es siempre el mismo número, y el
día que no lo sea, se nota.

El fondo vive en `FONDO_FIJO_SUGERIDO`: la apertura lo propone y quien abre
puede corregirlo. Va como parámetro y no clavado en el código para que
cambiarlo sea una variable de entorno.

### D-16 · No se modeló el punto de cobro como entidad

Hay un solo cajón y no se esperan más, así que la sesión es la entidad de más
arriba.

**Por qué esta omisión no compra deuda**, a diferencia de la de sucursales que
se descartó con el análisis viejo: si mañana aparece un segundo cajón, todas
las sesiones históricas pertenecieron al primero y el relleno es unívoco. Con
el stock por sucursal no era así — había que inventar a qué local perteneció
cada movimiento.

### D-17 · Todo peso que entra o sale pasa por un solo lugar

`caja_service.registrar_movimiento` es la única función que escribe en
`movimiento_caja`. La apertura, el cierre, los movimientos a mano y —cuando
exista— el cobro de una venta la llaman con su tipo.

Mismo razonamiento que la auditoría automática (D-2): si cada módulo anotara
por su cuenta, alcanzaría con que uno se olvide para que el arqueo quede sin
explicación.

Una salida que dejaría el cajón en negativo se rechaza: es una acción que está
por pasar. La diferencia del arqueo, en cambio, nunca se rechaza, porque
refleja algo que ya pasó y frenarla no trae la plata de vuelta.

---

## 5. Las ventas

Una venta es un **documento histórico**, no una vista de los datos de hoy. Ese
principio explica casi todas las decisiones que siguen.

### D-18 · El catálogo es opcional, y la línea escrita a mano siempre está

Una línea de venta puede salir de un artículo del catálogo o escribirse a
mano. Las dos conviven.

**El motivo es de adopción, no técnico.** Un local que vende de todo
—zapatillas, bermudas, mallas, remeras, camperas, gorras, billeteras— necesita
días de carga para tener un catálogo completo. Un módulo de ventas que exige
ese catálogo antes de la primera venta corre serio riesgo de no usarse nunca:
se sigue vendiendo con el cuaderno mientras el sistema espera que alguien
termine de cargarlo.

Con el híbrido se vende desde el primer día y el catálogo crece por donde
duele: lo que más se repite. Cada artículo cargado ahorra tipeo y mejora los
reportes, sin frenar nada.

**Lo que se resigna, y está aceptado**: mientras haya líneas escritas a mano,
"Campera azul" y "campera azul" son dos cosas distintas para cualquier
reporte. Es el costo de poder empezar.

### D-19 · El artículo es plano y el talle vive en la línea

"Zapatilla Nike Air" es **un** artículo, no uno por número. El talle se anota
al vender, en la línea.

**Alternativa descartada**: un artículo por combinación de talle y color, que
es lo que hacía el catálogo retirado. Es lo correcto el día que haya que
controlar existencias, y hoy no hay que controlarlas. Mientras tanto
multiplica por veinte las filas a cargar sin agregar nada: con el talle en la
línea igual se puede contestar en qué talles se vende cada modelo.

El día que entre el control de stock, esa decisión se revisa. El relleno no es
trivial —hay que abrir cada artículo en sus talles— pero es acotado y con las
ventas ya registradas se sabe qué talles existen de verdad.

### D-20 · La línea guarda el precio con el que se vendió

`descripcion` y `precio_unitario` son copias, aunque la línea apunte a un
artículo del catálogo.

**Alternativa descartada**: traer el precio por referencia. El día que suben
los precios cambiarían todas las ventas anteriores, y los reportes de
rentabilidad mentirían hacia atrás sin que nadie se entere. Hay un test que lo
comprueba: se vende, se cambia el precio del artículo, y la venta sigue
diciendo lo mismo.

### D-21 · El pago de una venta no es una tabla propia

Cada cobro **es** un movimiento de caja, con su medio de pago y con las
columnas de documento apuntando a la venta. No hay una tabla `pago_venta`.

Duplicarlo sería tener dos versiones del mismo dato que se pueden
desincronizar, y ya se está aplicando el criterio opuesto en todo el sistema:
lo que se copia es un **estado histórico** (el precio de una línea), no un
dato que vive en otro lado.

**Cuándo se revisa**: el día que exista un pago que no toque la caja —una
cuenta corriente— la venta va a necesitar registrar algo que la caja no
conoce. El relleno desde los movimientos es unívoco, así que la omisión es
barata.

### D-22 · No se vende con la caja cerrada

Toda venta pertenece a una sesión de caja. Sin sesión abierta, la API
responde 409 y dice qué hacer.

**Lo que cuesta**: la primera venta del día se frena hasta que alguien abra la
caja, con el cliente enfrente. **Lo que compra**: que no exista una sola venta
fuera de un arqueo. La alternativa —abrir la caja sola con el fondo sugerido—
resuelve el mostrador y arruina el arqueo, porque el monto de apertura pasa a
ser un número que nadie contó.

### D-23 · Anular no borra, y la reversión va a la caja de ahora

Una venta anulada queda marcada, con quién la anuló y por qué, y el sistema
genera los cobros al revés para que el arqueo siga cuadrando.

Las reversiones van a la **sesión abierta en este momento**, no a la sesión
original de la venta. Si fueran a la original y esa caja ya estuviera cerrada,
se estaría tocando un arqueo congelado: el número que alguien contó y firmó
dejaría de coincidir con sus movimientos. Es el mismo criterio de una nota de
crédito, que se emite el día que se emite y no se mete en el mes ya cerrado.

Consecuencia aceptada: no se puede anular sin una caja abierta, porque la
plata tiene que volver a alguna.

### D-24 · Las cuentas del mostrador se hacen en centavos enteros

`lib/carrito.ts` convierte todo a centavos antes de sumar y vuelve a texto al
mandarlo.

Sumando en pesos, `0.1 + 0.2` da `0.30000000000000004` en JavaScript. Ese
centavo de más se cobra mal y recién aparece en el arqueo del cierre, cuando
ya nadie se acuerda de qué venta salió. Está aparte de la pantalla y testeado
porque es la parte que no puede estar mal.

---

## 6. Cómo se construye: en rodajas verticales

No se hace el modelo completo de todos los módulos y después las pantallas. Se
hace de punta a punta, tanda por tanda, y cada tanda deja el sistema
funcionando.

Los tests quedan en verde en cada tanda. Si algo queda rojo es una regresión,
no ruido de fondo, y no se avanza con el CI roto.

| # | Tanda | Estado |
|---|---|---|
| 1 | Base: repo, CI, ingreso con roles, marco de pantallas, auditoría automática, migraciones | **Hecha** |
| 2 | Caja: medios de pago, apertura, movimientos, arqueo ciego y cierre | **Hecha** (24/08/2026) |
| 3 | Ventas: catálogo opcional, venta con varios medios de pago, anulación | **Hecha** (24/08/2026) |
| 4+ | A definir | Pendiente |

---

## 7. Endurecimiento operativo

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

Sobre Supabase: en producción va la URL del **session pooler**
(`aws-0-<región>.pooler.supabase.com`, puerto 5432). La URL directa resuelve
solo a IPv6 y Railway sale por IPv4: falla con "Network is unreachable". El
puerto 6543 del mismo host es el *transaction* pooler, que rompe las consultas
preparadas de asyncpg. El paso a paso está en `docs/despliegue.md`.

---

## 8. Lo que se quitó el 24/08/2026, y qué se aprendió

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
