# Registro de cambios

Un apartado por módulo. Se anota lo que cambia para quien usa el sistema, no
cada commit.

Formato de fechas: dd/mm/aaaa.

---

## Base (auth, sucursales, usuarios, auditoría)

### 20/08/2026 — tanda 1

**Agregado**

- Ingreso al sistema con correo y contraseña, con tres puestos: administrador,
  encargado y vendedor.
- Cambio de la contraseña propia.
- Sucursales: alta, listado y modificación. Un depósito es una sucursal que no
  vende ni abre caja.
- Usuarios: alta, listado, modificación y baja. La baja desactiva la cuenta;
  no borra a la persona de las operaciones que hizo.
- Registro de auditoría: cada alta, cambio y baja de cualquier parte del
  sistema queda guardada con quién y cuándo, sin que haya que activarla.
- Ayuda en pantalla en cada sección, con las preguntas que aparecen al usarla.

**Decidido**

- Vender sin existencias queda bloqueado.
- Las devoluciones no entregan efectivo: cambio o nota de crédito.
- El plazo de cambio es de 30 días con ticket.

---

## Catálogo

Sin cambios todavía. Entra en la tanda 2.

## Stock

Sin cambios todavía. Entra en la tanda 3.

## Punto de venta y caja

Sin cambios todavía. Entra en la tanda 4.

## Devoluciones y cambios

Sin cambios todavía. Entra en la tanda 5.

## Facturación

Sin cambios todavía. El comprobante se modela en la tanda 6 y queda apagado
hasta tener los certificados.
