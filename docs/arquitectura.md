# Arquitectura — Anorak

Este archivo dice **por qué** el sistema es como es. El código ya dice qué
hace; lo que no se puede leer del código es qué alternativa se descartó y a
cambio de qué. Cuando una regla cambie, se actualiza el razonamiento acá, no
solo el código.

Última revisión: 20/08/2026 (tanda 1).

---

## 1. Qué es y para quién

Un sistema web para administrar un local de ropa: catálogo con variantes de
talle y color, control de existencias y punto de venta. Va a crecer hasta
cubrir compras, clientes, caja, reportes y facturación electrónica.

Quien lo usa atiende un mostrador. Eso condiciona todo: las operaciones tienen
que resolverse rápido, con el cliente enfrente, muchas veces desde un celular
y a veces sin internet.

El negocio es en Argentina: la facturación es contra ARCA (ex AFIP) y la
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
interfaz sea una PWA instalable con capacidad offline —que es un requisito, no
un lujo— y que cada parte se despliegue donde mejor le queda: CDN para los
estáticos, contenedor para la API.

---

## 3. Las decisiones de modelado

Son las caras de cambiar después. Cada una está tomada de una manera y no de
otra por una razón concreta.

### D-1 · Producto → Variante → Stock. El stock nunca cuelga del producto

```
producto        (nombre, categoría, marca, temporada, género, descripción)
  └── variante  (talle, color, SKU, código de barras)
        └── stock  (variante_id + sucursal_id → cantidad)
```

En ropa, lo que se vende, se cuenta y se repone es "remera negra talle M". El
producto es el molde; la variante es la unidad real.

**Alternativa descartada**: colgar el stock del producto y guardar el talle
como un dato más de la línea de venta. Es más simple de arrancar y no
sobrevive a la primera pregunta del mostrador: "¿la tenés en M?". Peor: meter
`variante_id` en una tabla de existencias que ya tiene movimientos históricos
obliga a inventar a qué variante correspondía cada movimiento viejo, y esa
información no está en ningún lado.

### D-2 · Multi-sucursal desde la primera migración

`sucursal_id` viaja en existencias, ventas, caja y usuarios desde el día uno,
aunque hoy haya un solo local (respuesta del dueño, 20/08/2026).

**Alternativa descartada**: agregarlo cuando abra el segundo local. El
problema es el mismo que D-1 y peor: cada movimiento histórico quedaría sin
sucursal, y no hay forma de deducirla después. El costo de tenerlo desde el
principio es una columna y un selector; el de agregarlo después es un día de
trabajo y una decisión arbitraria sobre datos ya cerrados.

El depósito, si algún día existe, es una sucursal más con `tipo = DEPOSITO`:
tiene existencias y recibe envíos, pero no vende ni abre caja. No es una
entidad aparte porque todo lo que se hace con la mercadería —contarla,
moverla, ajustarla— es idéntico en los dos casos.

### D-3 · El movimiento de stock es un hecho y no se borra

Toda variación de existencias —venta, compra, ajuste, transferencia,
devolución, conteo— deja un movimiento con su tipo, su motivo, quién y cuándo.
El stock actual se mantiene como número y además se puede reconstruir sumando
movimientos.

Que existan las dos cosas es a propósito: **si los dos números no coinciden,
hay un bug y tiene que notarse**. Un sistema que solo guarda el saldo no puede
detectar que se corrompió.

Una transferencia entre sucursales son **dos** movimientos y un estado
intermedio: salió de A, todavía no llegó a B.

**Alternativa descartada**: un solo movimiento instantáneo que resta de A y
suma a B. Es más corto de escribir y hace desaparecer la mercadería que está
viajando: no está en ninguna de las dos sucursales, o está en las dos.

### D-4 · La línea de venta guarda el precio con el que se vendió

Snapshot, no referencia. La línea guarda el precio, el nombre del producto y
el costo del momento.

**Alternativa descartada**: traer el precio por join a la variante. El día que
sube el precio cambian todas las ventas viejas, y los reportes de rentabilidad
mienten hacia atrás sin que nadie se entere. Una venta es un documento
histórico, no una vista de los datos de hoy.

### D-5 · La devolución y el cambio son documentos propios

En ropa, el cambio de talle es la operación posventa más común: entra una
variante, sale otra, y puede haber diferencia de precio a favor de cualquiera
de las dos partes. Se modela como un documento que referencia la venta
original.

**Alternativa descartada**: registrar una venta en negativo. Parece más simple
hasta que hay que contestar "¿cuánto vendí realmente?" —las ventas negativas
ensucian todos los totales— o "¿qué talles se cambian más?", que es justamente
el dato que le dice al local qué está comprando mal.

Reglas del negocio (respuestas del dueño, 20/08/2026):

- **Nunca se devuelve efectivo.** La devolución termina en un cambio directo o
  en una nota de crédito con saldo a favor. La caja no entrega plata por una
  devolución, así que el arqueo no tiene que contemplar ese egreso.
- **30 días de plazo, con ticket obligatorio.** El plazo va como parámetro
  (`DIAS_PLAZO_CAMBIO`), no clavado en el código.

### D-6 · La caja se abre y se cierra, y cada cobro dice dónde termina la plata

Una sesión de caja tiene apertura con monto inicial, movimientos, y cierre con
arqueo: lo declarado contra lo calculado, y la diferencia **registrada, no
corregida a mano**. Una diferencia que se puede editar hasta que cierre deja
de ser información.

Cada pago dice su medio y su destino: el efectivo va a la caja física, la
tarjeta y el QR van a una cuenta y acreditan después, la transferencia a otra.

El pago es una tabla aparte y no dos columnas en la venta, porque una venta se
paga con varios medios a la vez —mitad efectivo, mitad tarjeta— y eso es
normal en un local, no un caso raro.

### D-7 · El precio tiene historia

Costo, precio de venta y precio mayorista, con registro de quién los cambió y
cuándo.

En un local de ropa el margen es el negocio. Sin historial de precios no se
puede explicar por qué cayó, que es exactamente la pregunta que aparece
cuando cae.

El precio mayorista queda modelado aunque hoy no se venda por mayor (respuesta
del dueño: solo minorista). Es una columna sin usar, no una tabla de listas de
precios: agregar la columna después sería trivial, pero tener el historial de
precios ya escrito con una sola dimensión y tener que abrirlo a N listas no lo
es.

---

## 4. Las respuestas que fijaron el modelo

Preguntas contestadas por el dueño el 20/08/2026, con lo que cada una decide:

| Pregunta | Respuesta | Qué fija |
|---|---|---|
| Sucursales | Una, sin depósito | Multi-sucursal igual (D-2). Transferencias quedan para el final |
| Venta por mayor | Solo minorista | Precio mayorista como columna, no lista de precios (D-7) |
| Talles | Catálogo cerrado por categoría | Tabla de curvas de talle; la variante referencia el catálogo. Evita que convivan "M" y "m" |
| Devoluciones | Cambio o nota de crédito, nunca efectivo | La caja no registra egresos por devolución (D-5) |
| Plazo de cambio | 30 días, con ticket | Parámetro `DIAS_PLAZO_CAMBIO`; el cambio se busca por número de ticket |
| Descuentos | Manuales, por línea y sobre el total | Sin motor de promociones. Tope por rol y motivo registrado |
| Comisiones | No | Sin vendedor como entidad. `created_by` de la venta es el gancho si algún día se necesita |
| Venta sin stock | Se bloquea | Ver D-8 |

### D-8 · Vender sin existencias está bloqueado, pero detrás de un parámetro

El dueño eligió bloquear. Se implementa bloqueando.

Queda anotado que el propio pedido reconocía el riesgo —"bloquear puede
significar perder la venta con el cliente enfrente"—, y por eso la regla vive
en `PERMITIR_STOCK_NEGATIVO` (default `false`) y no en un `if` clavado. El día
que el mostrador pida lo contrario, es cambiar una variable de entorno, no
migrar la base ni reescribir el circuito de venta.

---

## 5. El punto de venta tiene que vender sin internet

Es el requisito que más condiciona la arquitectura, así que está presente
desde el diseño aunque se implemente al final.

Un local con la conexión caída no puede dejar de vender. La venta se registra
local en IndexedDB (Dexie), se encola, y se sincroniza al reconectar, con un
cartel visible del estado: "Sin conexión — guardando acá", "Sincronizando",
"Al día".

Eso obliga a dos cosas **desde ahora**, no cuando se implemente:

1. **El identificador de la venta se genera del lado del cliente**: UUID, no
   autoincremental. Por eso toda tabla lleva `id` uuid PK y
   `app/models/base.py::generate_uuid` existe desde la primera migración. Un
   id que solo existe una vez que el servidor contestó haría imposible el
   circuito.
2. **El backend tiene que ser idempotente** al recibir una venta que ya
   recibió. Si el celular sincroniza dos veces porque se cortó la respuesta,
   no puede haber dos ventas.

La numeración fiscal es la excepción: esa la asigna el servidor al autorizar
el comprobante, nunca el cliente.

Lo que **no** se hace: cachear las respuestas de la API con Workbox. Una
respuesta de stock guardada de ayer es peor que no tener respuesta, porque se
lee como verdadera. Lo que funciona sin conexión es la cola de ventas, que es
un mecanismo explícito y visible.

---

## 6. Facturación: preparada y apagada

El comprobante está modelado; el servicio de ARCA vive detrás de
`ARCA_HABILITADO` (default `false`), y los endpoints fiscales devuelven 503
mientras esté apagado. **No se llama nunca a la API real de ARCA ni a
homologación**: eso lo prueba el dueño cuando tenga los certificados.

Dos diferencias con un sistema de facturación pensado para clientes empresa:

- Un local de ropa vende a consumidor final, así que necesita **Factura B y
  ticket**, no solo Factura A. La A es para el cliente mayorista responsable
  inscripto. El tipo de comprobante sale de la condición de IVA del cliente, y
  si no hay cliente identificado, es consumidor final.
- **La mayoría de las ventas no llevan cliente.** Identificarlo no puede ser
  obligatorio para vender: en un local, eso frena la cola.

Regla que se mantiene: **el cargo en cuenta corriente nace con el CAE, nunca
antes**. Un comprobante sin autorizar no mueve el saldo de nadie.

---

## 7. Decisiones técnicas

### D-9 · Los tests corren sobre SQLite en memoria

La suite corre en una máquina recién clonada: sin `.env`, sin Docker, sin
PostgreSQL, sin red. El costo es no poder usar tipos nativos de PostgreSQL en
los modelos, y por eso existen `UUIDType` y `FlexibleJSON` en
`app/core/types.py`.

El beneficio es que los tests corren en segundos y nadie tiene excusa para no
correrlos. Un test que necesita infraestructura es un test que no se corre.

Consecuencia: las migraciones se autogeneran contra SQLite. Funciona porque
todos los tipos son portables, pero **el archivo generado hay que leerlo**
antes de commitearlo.

### D-10 · La auditoría se escribe sola

Un único listener sobre `before_flush` (`app/core/audit.py`) registra cada
alta, cambio y baja de cualquier tabla, y completa `created_by`/`updated_by`.

**Alternativa descartada**: que cada service llame a un `registrar_cambio()`.
Alcanza con un endpoint nuevo escrito apurado para que un cambio quede sin
rastro, y eso se descubre el día que hace falta saber quién tocó un precio.
Lo que depende de que alguien se acuerde, algún día no se hace.

Límite conocido y aceptado: si una columna nunca se leyó de la base y se le
asigna un valor, el valor anterior se pierde en el momento de la asignación
—ni `load_history()` lo recupera— y el registro queda con el "después" sin el
"antes". En la práctica no aparece, porque los endpoints traen la fila con
`db.get()` antes de tocarla, y eso carga todas las columnas.

### D-11 · `created_by`/`updated_by` no tienen clave foránea

Están en **todas** las tablas, incluida `sucursal`, y `usuario` a su vez
apunta a `sucursal`. Con la clave foránea puesta, eso es un ciclo: PostgreSQL
no puede ordenar la creación de las tablas y la primera migración no corre.

Lo que se pierde es poco: las cuentas se dan de baja de forma lógica y nunca
se borran, así que un `created_by` apuntando a la nada no puede ocurrir.
`audit_log.usuario_id` sí conserva su clave foránea: esa tabla no participa
del ciclo.

### D-12 · El token de la sesión vive en memoria

Ni `localStorage` ni `sessionStorage`: cualquier script que corra en la página
los lee, y el token es la llave de todo el sistema.

El costo es real y está aceptado: al recargar la pestaña hay que volver a
entrar. Para un sistema que se usa con la pestaña abierta toda la jornada, es
barato. El manual lo explica, porque si no se explica se lee como una falla.

### D-13 · Un solo componente de listado para las tres pantallas

`<Listado>` se dibuja como tabla en pantalla ancha y como tarjetas en pantalla
angosta, desde una sola definición de columnas.

**Alternativa descartada**: mantener dos listados en paralelo. El que se usa
menos —siempre el de tarjetas— se olvida de mostrar la columna nueva, y nadie
lo nota hasta que alguien busca ese dato desde el celular.

Regla emparentada: ningún campo de carga por debajo de 16px. Por debajo de
eso, iPhone amplía la pantalla solo al tocarlo, y quien está cobrando tiene
que salir del zoom a mano en cada campo.

### D-14 · Las fechas, siempre en dd/mm/aaaa y con componente propio

Los formateadores viven en `lib/fecha.ts` y la carga se hace con
`<CampoFecha>`, nunca con `<input type="date">`: el control nativo lo dibuja
el navegador con el formato de la máquina, no con el del sitio. En una
computadora con Windows en inglés, la misma pantalla que **muestra**
05/03/2026 **pide** 03/05/2026. Nadie lo nota hasta que un movimiento queda
fechado dos meses después.

Detalle del que ya hay test: una fecha sola (`2026-03-05`) se arma en horario
local. Con `new Date('2026-03-05')`, JavaScript la lee como medianoche UTC y
en Argentina la muestra un día antes.

### D-15 · La ayuda en pantalla es la fuente del manual

Todos los textos de ayuda viven en `lib/ayuda.ts`, no sueltos dentro de cada
pantalla. Tres razones: se leen de una sola vez y hablan con una sola voz; el
dueño los puede corregir sin tocar el código de una pantalla; y el manual de
usuario se **arma** de ahí en lugar de reescribirse.

Si cada pantalla tuviera su texto suelto, el manual y el sistema se
contradirían el primer día que alguien cambie uno de los dos.

Regla al escribirlos: cuando el sistema **no deja** hacer algo, la ayuda dice
por qué. Un "no se puede" sin motivo se lee como que el sistema está roto, y
la persona termina llamando por teléfono en vez de resolverlo sola.

### D-16 · Los enum se guardan como texto, con conversión de ida y vuelta

`enum_texto()` en `app/core/types.py`. No es el tipo ENUM nativo de PostgreSQL
—sumar un estado no debe obligar a migrar un tipo, y además tiene que
funcionar en SQLite— pero tampoco es un `String` pelado.

La diferencia importa: con `String` y anotación `Mapped[MiEnum]`, el objeto
recién creado en Python conserva el enum y los tests pasan, pero la fila
leída de la base vuelve como `str` y cualquier `.value` explota. Se descubrió
probando el ingreso a mano, con la suite entera en verde.

---

## 8. Cómo se construye: en rodajas verticales

No se hace el modelo completo de los doce módulos y después las pantallas. Se
hace de punta a punta, tanda por tanda, y cada tanda deja el sistema
funcionando.

| # | Tanda | Estado |
|---|---|---|
| 1 | Base: repo, CI, auth con roles, layout, auditoría automática, migraciones | **Hecha** (20/08/2026) |
| 2 | Catálogo: productos, variantes, categorías, marcas, imágenes, precios | Pendiente |
| 3 | Stock: existencias por variante y sucursal, movimientos, ajustes, alertas de mínimo | Pendiente |
| 4 | POS: venta, medios de pago, caja abierta/cerrada, ticket en PDF | Pendiente |
| 5 | Devoluciones y cambios | Pendiente |
| 6 | Compras y proveedores, clientes y cuenta corriente, reportes, facturación, transferencias, conteos físicos | Pendiente |

Los tests quedan en verde en cada tanda. Si algo queda rojo es una regresión,
no ruido de fondo, y no se avanza con el CI roto.

---

## 9. Módulos que no se implementan ahora

No se escriben todavía, pero quedan documentados con la decisión de hoy que
los va a afectar. Es lo que evita que "lo agregamos después" se convierta en
"hay que rehacer el modelo".

### E-commerce

Vendería contra el mismo catálogo y el mismo stock.

**Qué lo afecta hoy**: D-1 y D-2. Que el stock cuelgue de la variante y no del
producto es lo que permite publicar "talle M agotado" sin bajar la
publicación entera. Que el stock esté por sucursal permite reservar de un
punto concreto. Lo que va a faltar es un **estado de reserva**: la unidad que
un pedido web tomó pero todavía no salió del local no está vendida ni está
disponible. Encaja como un tipo más de movimiento (D-3), sin tocar el modelo.

### RRHH: comisiones, turnos, asistencia

El dueño respondió que hoy no hay comisiones y que el dato de vendedor no
interesa.

**Qué lo afecta hoy**: la venta guarda `created_by` por auditoría automática
(D-10). Ese es el gancho: si algún día hay comisiones, el "quién vendió" ya
está registrado en todas las ventas históricas y no hay que inventarlo. Lo
que va a faltar es el vendedor como **entidad de negocio** —con porcentaje,
liquidación y período—, que es una tabla nueva, no una migración de las
ventas ya hechas.

### Conciliación bancaria

**Qué lo afecta hoy**: D-6. Que cada pago diga su medio y su **destino** —y
que tarjeta y QR acrediten después, no en el momento— es exactamente lo que
después se concilia contra el extracto. Si el pago fuera dos columnas en la
venta, no habría contra qué conciliar. Lo que va a faltar es la fecha de
acreditación esperada y la comisión del medio de pago: dos columnas en la
tabla de pagos.

### Fidelización de clientes

**Qué lo afecta hoy**: la decisión de que **la mayoría de las ventas no llevan
cliente** (sección 6). Un programa de puntos solo puede contar las ventas
identificadas, y eso está bien: es el incentivo para identificarse. Lo que no
hay que hacer nunca es volver obligatorio el cliente para vender, porque eso
frena la cola por un beneficio que es opcional.

---

## 10. Endurecimiento operativo

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
