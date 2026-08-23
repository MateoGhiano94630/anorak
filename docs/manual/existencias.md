# Existencias

Acá se ve cuánto hay de cada prenda en cada local, se carga la mercadería que
llega y se corrige lo que no coincide.

## Lo que muestra la lista

Cada fila es **una prenda en un talle, un color y un local**. La misma remera
en M y en L son dos filas, y si tenés dos locales, cada uno lleva las suyas.

Es a propósito: es lo que permite contestar "¿la tenés en M?" y "¿la tenés
acá?", que son dos preguntas distintas.

Una prenda aparece en esta lista recién cuando entra su primera unidad. Una
prenda del catálogo que nunca se cargó todavía no tiene existencias.

El triángulo ⚠ al lado de la cantidad quiere decir que llegó a su punto de
reposición.

## Cargar mercadería que llegó

Abajo de la lista está el formulario de carga. Se usa cuando llega un pedido:

1. Escribí o pasá el lector por el **código de la prenda**. Sirve el código
   interno o el de barras.
2. Elegí el local que la recibe.
3. Poné cuántas unidades entraron y el motivo.

Se busca por código y no eligiendo de una lista porque, con la caja de bolsas
al lado, buscar una combinación entre cientos es impracticable. El código está
en la etiqueta.

## Corregir por conteo

Tocá la fila de la prenda y se abre un panel.

- **Llegó mercadería** suma unidades. Es lo mismo que el formulario de abajo,
  pero para una prenda que ya está en la lista.
- **Conté y hay** es para cuando el número no coincide: escribís cuántas
  encontraste de verdad y el sistema guarda la diferencia.

Las dos operaciones piden un **motivo**, y es obligatorio. Dentro de tres
meses, un número que cambió sin explicación no lo va a poder justificar nadie.
Con "se mojaron dos" o "conteo del lunes" alcanza.

Si contás y da lo mismo que decía el sistema, no se registra nada: no hubo
ningún cambio que explicar.

### ¿Por qué me deja poner un número más bajo?

Porque el conteo refleja algo que ya pasó. Si contaste tres y el sistema decía
cinco, esas dos prendas ya no están, y que el sistema se niegue a anotarlo no
las trae de vuelta: solo lo deja mintiendo con más convicción.

Es distinto de una venta: ahí el sistema sí frena, porque la venta todavía no
pasó y se está por hacer con mercadería que no hay.

## El punto de reposición

En el mismo panel está **Reponer cuando llegue a**. Cuando la cantidad llega a
ese número o baja, la prenda aparece marcada y en el filtro "Solo lo que hay
que reponer".

Es la lista que se mira antes de llamar al proveedor: dice qué se está por
acabar mientras todavía queda algo para vender.

**Cero quiere decir que esa prenda no se controla.** Si todas avisaran, la
lista se llenaría de prendas de temporada pasada que ya no se reponen y
dejaría de servir para decidir un pedido.

Se puede fijar el mínimo antes de que llegue la primera unidad: así la prenda
aparece en las alertas desde el primer día.
