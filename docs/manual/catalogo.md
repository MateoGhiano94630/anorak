# El catálogo

El catálogo son todas las prendas que vende el local. Desde acá se cargan, se
buscan y se les pone precio.

## Prenda, talle y color: cómo lo entiende el sistema

Esta es la idea que hay que tener clara; todo lo demás sale de ella.

- La **prenda** es el modelo: "Remera de algodón Nike". No tiene talle ni
  color: es el molde.
- Lo que se vende, se cuenta y se repone es cada **combinación de talle y
  color**: la negra en M es una cosa y la blanca en L es otra. Cada una tiene
  su propio código, su propio precio y sus propias existencias.

Por eso se carga primero la prenda y después se generan todas sus
combinaciones de una vez.

Es lo que permite contestar "¿la tenés en M?" sin ir al depósito a mirar.

## Cargar una prenda

1. Entrá a **Catálogo** y tocá **Nueva prenda**.
2. Poné el nombre, elegí la categoría y, si tiene, la marca.
3. Elegí para quién es y de qué temporada.
4. Tocá **Crear y cargar talles**. El sistema te lleva directo a la prenda,
   porque lo siguiente siempre es cargarle los talles.

### ¿Por qué me pide una categoría?

Porque la categoría es la que dice qué talles existen para esa prenda. Las
remeras van de S a XL y el calzado del 35 al 45. Es lo que evita cargar una
remera en talle 42 por error.

Si todavía no tenés ninguna categoría, el sistema te avisa y te lleva a la
pantalla donde se crean.

## Buscar

El buscador encuentra por cualquier parte del nombre: escribiendo "lisa"
aparecen todas las remeras lisas. El filtro de categoría acota a un tipo de
prenda.

## Lo que muestra el listado

Cada fila trae la foto, la prenda, la categoría, la marca, cuántas
combinaciones de talle y color tiene, y el precio.

**Dos precios separados por un guion** quieren decir que no todos los talles
valen lo mismo: son el más barato y el más caro. Si todos valen igual, aparece
un solo precio.

**"Sin precio"** quiere decir que todavía no se le puso ninguno. Esa prenda no
se va a poder vender hasta que tenga uno: el sistema prefiere frenar antes que
cobrarla como si valiera cero.

En el celular, cada prenda se ve como una tarjeta en lugar de como una fila de
tabla, para no tener que arrastrar la pantalla para los costados.
