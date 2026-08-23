/**
 * Todos los textos de ayuda del sistema, juntos en un solo archivo.
 *
 * Están acá y no sueltos dentro de cada pantalla por tres razones:
 *
 * 1. Se leen todos de una sentada, así que hablan con una sola voz.
 * 2. El dueño del local los puede corregir sin tocar el código de una pantalla.
 * 3. El manual de usuario se arma de este archivo. Si cada pantalla tuviera su
 *    texto suelto, el manual y el sistema se contradirían el primer día que
 *    alguien cambie uno de los dos.
 *
 * Cómo escribirlos:
 *
 * - Sin palabras de informática. Nada de "campo", "registro" ni "endpoint".
 * - Cuando el sistema **no deja** hacer algo, la ayuda dice por qué. Un "no se
 *   puede" sin motivo se lee como que el sistema está roto, y la persona
 *   termina llamando por teléfono en vez de resolverlo sola.
 */

export interface PreguntaAyuda {
  /** La duda tal como se la haría quien atiende el local. */
  pregunta: string
  /** La respuesta, en dos o tres oraciones. */
  respuesta: string
}

export interface AyudaPantalla {
  /** Nombre de la pantalla, tal como aparece en el menú. */
  titulo: string
  /** Para qué sirve la pantalla, en una oración. */
  resumen: string
  preguntas: PreguntaAyuda[]
}

export const AYUDA = {
  ingreso: {
    titulo: 'Entrar al sistema',
    resumen: 'Con tu correo y tu contraseña entrás a la parte que te toca.',
    preguntas: [
      {
        pregunta: '¿Por qué me pide entrar de nuevo si recargo la página?',
        respuesta:
          'El sistema no deja tu contraseña ni tu sesión guardadas en la computadora. ' +
          'Es a propósito: así, si alguien usa esa máquina después que vos, no entra ' +
          'con tu cuenta. Mientras no cierres la pestaña, seguís adentro.',
      },
      {
        pregunta:
          'Me dice que el correo o la contraseña están mal y estoy seguro de que no.',
        respuesta:
          'El aviso es el mismo para las dos cosas, así que puede ser cualquiera de ' +
          'las dos. Fijate que no haya quedado activada la tecla de mayúsculas. Si ' +
          'sigue sin entrar, pedile al administrador que te ponga una contraseña nueva.',
      },
      {
        pregunta: 'Me dice que mi cuenta está dada de baja.',
        respuesta:
          'Alguien con permiso de administrador desactivó tu cuenta. No se borran ' +
          'nunca, porque tu nombre quedó en las ventas y los movimientos que hiciste. ' +
          'Para volver a entrar, el administrador la tiene que activar otra vez.',
      },
    ],
  },
  inicio: {
    titulo: 'Inicio',
    resumen: 'La pantalla desde la que se llega a todo lo demás.',
    preguntas: [
      {
        pregunta: '¿Por qué no veo todas las opciones del menú?',
        respuesta:
          'Cada persona ve solo lo que le corresponde según su puesto. Quien atiende ' +
          'el mostrador ve el catálogo, el stock y las ventas; el encargado suma la ' +
          'caja y los ajustes; el administrador ve todo.',
      },
    ],
  },
  usuarios: {
    titulo: 'Usuarios',
    resumen:
      'Las cuentas de las personas que usan el sistema y qué puede hacer cada una.',
    preguntas: [
      {
        pregunta: '¿Qué diferencia hay entre los tres puestos?',
        respuesta:
          'Vendedor atiende el mostrador: vende y consulta precios y talles. ' +
          'Encargado maneja el local: además cierra la caja, autoriza devoluciones y ' +
          'corrige el stock. Administrador puede todo, incluidos los precios y estas ' +
          'mismas cuentas.',
      },
      {
        pregunta: '¿Cómo elimino una cuenta?',
        respuesta:
          'No se eliminan: se dan de baja. La persona deja de poder entrar, pero su ' +
          'nombre sigue figurando en las ventas y los movimientos que hizo. Si se ' +
          'borrara, esas ventas quedarían sin saber quién las hizo.',
      },
      {
        pregunta: '¿Por qué no puedo darme de baja a mí mismo?',
        respuesta:
          'Porque si sos el único administrador, el sistema quedaría sin nadie que ' +
          'pueda crear cuentas ni cambiar precios, y habría que arreglarlo desde ' +
          'afuera. Pedile a otro administrador que lo haga.',
      },
      {
        pregunta: '¿Puedo cambiarle la contraseña a otra persona?',
        respuesta:
          'Cada uno cambia la suya desde su propia cuenta. Si alguien la olvidó, el ' +
          'administrador le pone una nueva y esa persona la cambia al entrar.',
      },
    ],
  },
  sucursales: {
    titulo: 'Sucursales',
    resumen: 'Los locales y depósitos donde hay mercadería, caja y ventas.',
    preguntas: [
      {
        pregunta: 'Tengo un solo local. ¿Para qué sirve esta pantalla?',
        respuesta:
          'El sistema está preparado desde el principio para más de un local, aunque ' +
          'hoy haya uno solo. Cada venta, cada movimiento de mercadería y cada cierre ' +
          'de caja quedan guardados con el local al que pertenecen. Si el día de mañana ' +
          'abrís otro, no hay que rehacer nada de lo anterior.',
      },
      {
        pregunta: '¿Qué diferencia hay entre un local y un depósito?',
        respuesta:
          'Los dos tienen mercadería y reciben envíos. La diferencia es que el local ' +
          'vende y abre caja, y el depósito no: solo guarda y manda.',
      },
      {
        pregunta: '¿Por qué no puedo cambiar el código de una sucursal?',
        respuesta:
          'Porque ese código quedó escrito en los movimientos de mercadería y en las ' +
          'ventas ya hechas. Si se cambiara, esos movimientos pasarían a nombrar un ' +
          'local que no existe. El nombre sí se puede corregir cuando quieras.',
      },
    ],
  },
  catalogo: {
    titulo: 'Catálogo',
    resumen: 'Todas las prendas que vende el local, con sus talles, colores y precios.',
    preguntas: [
      {
        pregunta: '¿Qué diferencia hay entre una prenda y sus talles?',
        respuesta:
          'La prenda es el modelo: "Remera de algodón Nike". Lo que se vende y se ' +
          'cuenta es cada combinación de talle y color: la negra en M es una cosa y ' +
          'la blanca en L es otra. Por eso primero se carga la prenda y después se ' +
          'generan todas sus combinaciones de una vez.',
      },
      {
        pregunta: '¿Por qué me pide elegir una categoría antes de cargar la prenda?',
        respuesta:
          'Porque la categoría es la que dice qué talles existen para esa prenda. ' +
          'Las remeras van de S a XL y el calzado del 35 al 45. Es lo que evita ' +
          'cargar una remera en talle 42 por error.',
      },
      {
        pregunta: 'El listado muestra dos precios separados por un guion.',
        respuesta:
          'Es el precio más bajo y el más alto de esa prenda. Si todos los talles ' +
          'valen lo mismo, aparece un solo precio. Dos precios distintos quieren ' +
          'decir que algún talle o color tiene el suyo.',
      },
      {
        pregunta: 'Una prenda aparece sin precio.',
        respuesta:
          'Todavía no se le puso. Al mostrador no se le va a poder vender hasta que ' +
          'tenga uno: el sistema prefiere frenar antes que cobrarla como si valiera ' +
          'cero. Entrá a la prenda y usá "Poner precio a todo".',
      },
    ],
  },
  producto: {
    titulo: 'Una prenda',
    resumen: 'Los talles y colores de una prenda, sus códigos, sus precios y sus fotos.',
    preguntas: [
      {
        pregunta: '¿Qué es el código que aparece al lado de cada talle?',
        respuesta:
          'Es el código interno con el que el sistema reconoce esa prenda exacta. ' +
          'Lo propone el sistema con la marca, el nombre, el talle y el color, para ' +
          'que se pueda leer de un vistazo. Se puede corregir si preferís otro.',
      },
      {
        pregunta: '¿Y el código de barras?',
        respuesta:
          'Es el de la etiqueta del proveedor, cuando la trae. Es opcional: mucha ' +
          'ropa no viene con uno. Si lo cargás, el mostrador encuentra la prenda ' +
          'pasando el lector por la etiqueta.',
      },
      {
        pregunta: 'Agregué un color nuevo. ¿Tengo que cargar todo de nuevo?',
        respuesta:
          'No. Volvé a generar las combinaciones eligiendo todos los talles y el ' +
          'color nuevo: las que ya existían quedan como estaban y solo se agregan ' +
          'las que faltaban.',
      },
      {
        pregunta: '¿Por qué no puedo cambiar el precio?',
        respuesta:
          'Los precios los cambia solamente el administrador. Un descuento en una ' +
          'venta puntual es otra cosa y esa sí la puede hacer quien atiende, dentro ' +
          'del tope de su puesto.',
      },
      {
        pregunta: '¿Qué pasa con el precio anterior cuando lo cambio?',
        respuesta:
          'Queda guardado con la fecha hasta la que rigió. Nunca se pisa. Así una ' +
          'venta del mes pasado se puede explicar con el precio que tenía entonces, ' +
          'y se puede ver cómo fue cambiando el margen de esa prenda.',
      },
    ],
  },
  catalogosBase: {
    titulo: 'Marcas, colores y categorías',
    resumen: 'Las listas de las que salen las opciones al cargar una prenda.',
    preguntas: [
      {
        pregunta: '¿Por qué tengo que elegir el talle de una lista en vez de escribirlo?',
        respuesta:
          'Porque escrito a mano, en tres meses conviven "M" y "m" como si fueran ' +
          'dos talles distintos. Cuando quieras saber qué talles se te cambian más ' +
          '—que es lo que te dice qué estás comprando de más— el dato saldría ' +
          'partido en dos y no serviría.',
      },
      {
        pregunta: '¿Qué es una curva de talles?',
        respuesta:
          'Es el conjunto de talles que van juntos: S, M, L y XL para remeras; del ' +
          '35 al 45 para calzado. Cada categoría usa una, y así las prendas de esa ' +
          'categoría solo pueden cargarse en los talles que existen de verdad.',
      },
      {
        pregunta: 'Vendo algo que no tiene talle, como una gorra.',
        respuesta:
          'Creá una curva con un solo talle llamado "Único" y usala en esa ' +
          'categoría. El sistema pide siempre un talle porque es lo que le permite ' +
          'distinguir una prenda de otra sin equivocarse.',
      },
      {
        pregunta: '¿Puedo borrar una marca o un color que ya no uso?',
        respuesta:
          'No se borran: se desactivan. Dejan de aparecer al cargar prendas nuevas, ' +
          'pero las que ya estaban cargadas con ese color siguen mostrándolo. Si se ' +
          'borrara, esas prendas quedarían sin saber de qué color eran.',
      },
    ],
  },
  existencias: {
    titulo: 'Existencias',
    resumen: 'Cuánto hay de cada prenda en cada local, y qué se está por acabar.',
    preguntas: [
      {
        pregunta: '¿Cuál es la diferencia entre cargar mercadería y ajustar?',
        respuesta:
          'Cargar es para lo que llegó al local: sumás las unidades que entraron. ' +
          'Ajustar es para cuando contaste y no coincide: escribís cuánto hay de ' +
          'verdad y el sistema guarda la diferencia. Los dos quedan registrados, ' +
          'pero se leen distinto en el historial.',
      },
      {
        pregunta: '¿Por qué me pide un motivo para ajustar?',
        respuesta:
          'Porque dentro de tres meses, un número que cambió sin explicación no lo ' +
          'va a poder justificar nadie. Con "se mojaron dos" o "conteo del lunes" ' +
          'alcanza; lo importante es que quede escrito.',
      },
      {
        pregunta: 'Una prenda no aparece en la lista.',
        respuesta:
          'Las prendas aparecen acá recién cuando entra la primera unidad al local. ' +
          'Una prenda del catálogo que nunca se cargó no tiene existencias todavía: ' +
          'usá "Cargar mercadería" y aparece.',
      },
      {
        pregunta: '¿Qué es el mínimo?',
        respuesta:
          'El punto en el que conviene reponer. Cuando la cantidad llega a ese ' +
          'número o baja, la prenda aparece en las alertas, así te enterás mientras ' +
          'todavía queda algo para vender. Con el mínimo en cero, esa prenda no se ' +
          'controla.',
      },
      {
        pregunta: '¿Se puede vender algo que no tiene existencias?',
        respuesta:
          'No. El sistema lo frena. Es una decisión del local: prefiere avisar que ' +
          'no hay antes que dejar un número en negativo que después nadie entiende. ' +
          'Si de verdad hay una prenda que el sistema no registra, cargala primero ' +
          'y vendela después.',
      },
      {
        pregunta: 'El mismo modelo aparece dos veces con distinta cantidad.',
        respuesta:
          'Fijate el talle y el color: son dos prendas distintas para el sistema, ' +
          'y cada una tiene sus propias unidades. Si además tenés más de un local, ' +
          'cada local lleva las suyas.',
      },
    ],
  },
  movimientos: {
    titulo: 'Movimientos',
    resumen: 'Todo lo que entró y salió, con quién lo hizo y cuándo.',
    preguntas: [
      {
        pregunta: '¿Puedo borrar un movimiento que cargué mal?',
        respuesta:
          'No, y es a propósito. Un movimiento es algo que pasó: si se borrara, el ' +
          'sistema quedaría sin poder explicar de dónde salió un número. Lo que se ' +
          'hace es corregirlo con otro movimiento, igual que en un cuaderno de ' +
          'cuentas: se anota la corrección, no se tacha lo anterior.',
      },
      {
        pregunta: '¿Qué quiere decir la columna "quedó"?',
        respuesta:
          'Cuántas unidades había justo después de ese movimiento. Sirve para ' +
          'seguir la historia de una prenda de arriba hacia abajo y ver en qué ' +
          'momento pasó algo raro.',
      },
      {
        pregunta: 'Los números tienen signo más y menos.',
        respuesta:
          'El más es lo que entró y el menos lo que salió. Sumando toda la columna ' +
          'de una prenda tiene que dar exactamente lo que dice la pantalla de ' +
          'existencias. Si no diera, el sistema lo detecta solo y avisa.',
      },
    ],
  },
} as const satisfies Record<string, AyudaPantalla>

/** Los nombres de pantalla que tienen ayuda escrita. */
export type ClaveAyuda = keyof typeof AYUDA
