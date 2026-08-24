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

## Módulos de negocio

Sin definir. El alcance se está reanalizando.
