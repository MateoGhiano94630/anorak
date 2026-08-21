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

### 20/08/2026 — tanda 2

**Agregado**

- Curvas de talle: los conjuntos de talles que van juntos (S a XL, 35 al 45).
  Cada categoría usa una, y así una remera no se puede cargar en talle 42.
- Categorías, marcas y colores, con su tono para reconocerlos de un vistazo.
- Prendas: nombre, categoría, marca, para quién es y temporada.
- Generación de talles y colores de una vez: se eligen los talles y los
  colores y salen todas las combinaciones juntas. Volver a hacerlo para sumar
  un color no repite las que ya estaban.
- Código interno automático para cada combinación, legible desde la etiqueta
  (`NIKREMALG-M-NEG`), y código de barras del proveedor cuando lo trae.
- Búsqueda de una prenda por cualquiera de los dos códigos.
- Precios con historial: al cambiar uno, el anterior queda guardado con la
  fecha hasta la que rigió. Se puede poner el mismo precio a toda una prenda
  de una vez, o uno distinto por talle.
- Fotos de las prendas.
- Buscador y filtro por categoría en el catálogo, con el precio o el rango de
  precios de cada prenda.

**Decidido**

- Los precios los cambia solo el administrador.
- Una prenda sin precio no se va a poder vender: el sistema prefiere frenar
  antes que cobrarla como si valiera cero.

## Stock

Sin cambios todavía. Entra en la tanda 3.

## Punto de venta y caja

Sin cambios todavía. Entra en la tanda 4.

## Devoluciones y cambios

Sin cambios todavía. Entra en la tanda 5.

## Facturación

Sin cambios todavía. El comprobante se modela en la tanda 6 y queda apagado
hasta tener los certificados.
