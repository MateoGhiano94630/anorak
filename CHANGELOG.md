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
