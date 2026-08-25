# Registro de cambios

Un apartado por módulo. Se anota lo que cambia para quien usa el sistema, no
cada commit.

Formato de fechas: dd/mm/aaaa.

---

## Base (ingreso, usuarios, auditoría)

### 24/08/2026 — limpieza

**Quitado**

- Se retiraron el catálogo de prendas, los precios, las existencias y las
  sucursales. El análisis del que salieron no era correcto, así que el modelo
  de negocio que implementaban no servía.
- Los usuarios ya no pertenecen a una sucursal.

Todo lo retirado queda en el historial del proyecto: si alguna de esas
decisiones resulta acertada con el análisis nuevo, se recupera en vez de
rehacerse.

### 20/08/2026 — tanda 1

**Agregado**

- Ingreso al sistema con correo y contraseña, con tres puestos: administrador,
  encargado y vendedor.
- Cambio de la contraseña propia.
- Usuarios: alta, listado, modificación y baja. La baja desactiva la cuenta;
  no borra a la persona de las operaciones que hizo.
- Registro de auditoría: cada alta, cambio y baja de cualquier parte del
  sistema queda guardada con quién y cuándo, sin que haya que activarla.
- Ayuda en pantalla en cada sección, con las preguntas que aparecen al usarla.

---

## Ventas

### 24/08/2026 — primer módulo

**Agregado**

- Registrar una venta: se arma con lo que se lleva el cliente, se cobra y
  queda guardada con su número.
- Se puede vender **sin cargar nada antes**: la prenda se escribe a mano con
  su precio. El catálogo es opcional y sirve para no tipear lo mismo cada día.
- Catálogo de artículos, con un artículo por modelo. El talle se escribe al
  vender, así la lista queda corta.
- Descuentos por prenda y sobre el total de la venta.
- Cobro con varios medios a la vez: mitad efectivo y mitad tarjeta es normal
  en un mostrador. El sistema avisa si falta o sobra.
- Cálculo del vuelto en pantalla, que no se guarda en ningún lado.
- Los cobros entran a la caja del día: el efectivo al cajón, la tarjeta y el
  QR a la cuenta.
- Buscar una venta por su número o por lo que dice alguna de sus líneas.
- Anular una venta: no se borra, queda con el motivo y la plata vuelve a la
  caja abierta.

**Decidido**

- No se vende con la caja cerrada: así no queda ninguna venta fuera de un
  arqueo.
- Cada venta guarda el precio con el que se vendió. Cambiar el catálogo no
  toca las ventas anteriores.
- Anular una venta de un día ya cerrado devuelve la plata a la caja de hoy,
  no a la de ese día, que ya está contada y firmada.

**Todavía no**

- La venta no descuenta existencias: no hay control de stock.
- No hay ticket impreso; después de cobrar se muestra el resumen en pantalla.
- El mostrador necesita conexión para vender.

---

## Caja

### 24/08/2026 — primer módulo

**Agregado**

- Apertura de caja con el efectivo que hay en el cajón para dar vuelto. El
  sistema propone el fondo de siempre y se puede corregir.
- Registro de plata que se agrega, plata que se saca y gastos pagados de la
  caja, todos con motivo obligatorio y comprobante opcional.
- Cierre con arqueo: se cuenta el efectivo, se escribe lo que se encontró, y
  recién ahí el sistema muestra cuánto esperaba y cuál es la diferencia.
- Al cerrar se retira lo que sobra del fondo, y queda anotado.
- Historial de cierres con todas las diferencias juntas, para el encargado.
- Medios de pago: efectivo, débito, crédito, QR y transferencia, con su
  comisión y a cuántos días acreditan.

**Decidido**

- Hay una caja por jornada: la abre quien llega y cobran todos sobre ella.
- El arqueo es a ciegas. El sistema no dice cuánta plata debería haber hasta
  que se declara lo contado.
- La diferencia se registra y nunca se corrige.
- Un retiro o un gasto no puede dejar el cajón en negativo.
- Los movimientos no se borran: se corrigen con otro movimiento.

**Todavía no**

- La caja no cobra ventas: eso llega con el punto de venta. Por ahora funciona
  como un libro de caja.
