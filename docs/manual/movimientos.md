# Movimientos

Es el historial de todo lo que entró y salió: qué prenda, qué pasó, cuántas
unidades, cuánto quedó, quién lo hizo y cuándo.

## Cómo se lee

- **Qué pasó** dice el tipo: mercadería que llegó, corrección por conteo,
  venta, devolución, o mercadería que se movió entre locales.
- **Unidades** lleva signo: el más es lo que entró y el menos lo que salió.
- **Quedó** es cuántas unidades había justo después de ese movimiento. Sirve
  para seguir la historia de una prenda de arriba hacia abajo y ver en qué
  momento pasó algo raro.

Sumando toda la columna de unidades de una prenda tiene que dar exactamente lo
que muestra la pantalla de existencias. El sistema lo controla solo: si alguna
vez dejara de dar, lo detecta y lo avisa.

## No se puede borrar un movimiento

Y es a propósito.

Un movimiento es algo que pasó. Si se pudiera borrar, el sistema quedaría sin
poder explicar de dónde salió un número, y esa explicación es justamente para
lo que sirve tener el historial.

Una carga equivocada se arregla con otra: se corrige con un conteo, y quedan
las dos anotadas. Es como un cuaderno de cuentas, donde se anota la corrección
en vez de tachar lo anterior.

## Filtros

Se puede acotar por local y por tipo de movimiento. Por ejemplo, "corrección
por conteo" en un local muestra todas las veces que hubo que ajustar ahí, que
es el dato que dice si algo se está perdiendo.
