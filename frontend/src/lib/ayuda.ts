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
  caja: {
    titulo: 'Caja',
    resumen:
      'La caja del día: se abre al llegar, se registra lo que entra y sale, y se cierra al irse.',
    preguntas: [
      {
        pregunta: '¿Qué monto pongo al abrir?',
        respuesta:
          'El efectivo que hay en el cajón para dar vuelto, no lo que vendiste. ' +
          'El sistema te propone el mismo de siempre; si contaste y hay otra cosa, ' +
          'corregilo. Ese número es el punto de partida del arqueo del día.',
      },
      {
        pregunta: '¿Por qué no veo cuánta plata hay en la caja?',
        respuesta:
          'Es a propósito. Al cerrar vas a tener que contar el cajón y escribir lo ' +
          'que encontraste; si el sistema te mostrara el número antes, la tentación ' +
          'sería copiarlo y el control dejaría de servir para algo. Recién después ' +
          'de que declarás lo que contaste, el sistema te dice cuánto esperaba.',
      },
      {
        pregunta: '¿Cuándo uso "sacar plata" y cuándo "pagar un gasto"?',
        respuesta:
          'Sacar plata es llevarla al cofre o al banco: sigue siendo del negocio. ' +
          'Un gasto es plata que se fue: el flete, una compra chica. Los dos bajan ' +
          'el efectivo del cajón, pero en los números del negocio son cosas ' +
          'distintas, y por eso se anotan distinto.',
      },
      {
        pregunta: '¿Por qué me pide un motivo cada vez?',
        respuesta:
          'Porque dentro de tres meses, un movimiento de plata sin explicación no lo ' +
          'va a poder justificar nadie. Con "al cofre" o "flete del proveedor" ' +
          'alcanza; lo importante es que quede escrito quién lo hizo y por qué.',
      },
      {
        pregunta: 'Me dice que no hay tanto efectivo.',
        respuesta:
          'Estás intentando sacar más plata de la que el sistema registra en el ' +
          'cajón. Puede ser que falte cargar algo que entró, o que el monto de ' +
          'apertura no fuera el correcto. Fijate la lista de movimientos del día.',
      },
      {
        pregunta: '¿Puedo borrar un movimiento que cargué mal?',
        respuesta:
          'No. Un movimiento es plata que se movió: si se borrara, el sistema ' +
          'quedaría sin poder explicar el arqueo. Se corrige con otro movimiento, ' +
          'como en un cuaderno de cuentas, donde se anota la corrección en vez de ' +
          'tachar lo anterior.',
      },
      {
        pregunta: 'Alguien dejó la caja abierta de ayer.',
        respuesta:
          'El sistema no deja abrir una caja nueva mientras haya otra abierta, y te ' +
          'dice quién la abrió y cuándo. Cerrala vos contando lo que hay ahora: la ' +
          'diferencia va a quedar registrada, que es exactamente lo que tiene que ' +
          'pasar.',
      },
    ],
  },
  cierreCaja: {
    titulo: 'Cerrar la caja',
    resumen:
      'Se cuenta el efectivo, se compara con lo que el sistema esperaba y se guarda la diferencia.',
    preguntas: [
      {
        pregunta: '¿Qué cuento exactamente?',
        respuesta:
          'Todo el efectivo que hay en el cajón, incluido el fondo con el que ' +
          'abriste. La tarjeta, el QR y las transferencias no se cuentan: esa plata ' +
          'no está en el cajón, entra a la cuenta días después. El sistema te ' +
          'muestra esos totales aparte para que los cruces con el cierre del posnet.',
      },
      {
        pregunta: '¿Qué es "cuánto dejás para mañana"?',
        respuesta:
          'El fondo para dar vuelto al día siguiente. Lo que sobra de ese número se ' +
          'retira, y el sistema lo anota como un movimiento. Así todos los días ' +
          'arrancan con el mismo monto, y el día que no arranque igual, se nota.',
      },
      {
        pregunta: 'El arqueo no coincide.',
        respuesta:
          'Contá de nuevo antes de cerrar: la mayoría de las diferencias son un ' +
          'billete mal contado. Si igual no coincide, escribí qué creés que pasó y ' +
          'cerrá. La diferencia queda guardada tal cual, no se corrige: un número ' +
          'que se puede arreglar deja de ser información.',
      },
      {
        pregunta: '¿Qué pasa si me falta plata?',
        respuesta:
          'Se registra el faltante con tu explicación y la caja se cierra igual. El ' +
          'sistema no te acusa de nada: lo que importa no es un faltante suelto, ' +
          'sino si se repite. Por eso el encargado ve el historial de todos los ' +
          'cierres junto.',
      },
      {
        pregunta: '¿Y si sobra?',
        respuesta:
          'También queda registrado. Que sobre no es una buena noticia: casi siempre ' +
          'quiere decir que un cobro no se registró, así que esa venta no está en ' +
          'ningún lado.',
      },
    ],
  },
  historialCaja: {
    titulo: 'Cierres de caja',
    resumen:
      'Todos los cierres, con lo que se contó, lo que se esperaba y la diferencia.',
    preguntas: [
      {
        pregunta: '¿Para qué sirve esta pantalla?',
        respuesta:
          'Para mirar el conjunto, no un día suelto. Que un martes falten $500 no ' +
          'dice nada; que falten todos los martes, sí. Es la única forma de ver eso.',
      },
      {
        pregunta: '¿Se puede corregir una diferencia vieja?',
        respuesta:
          'No, y es a propósito. Lo que quedó guardado es lo que se contó ese día y ' +
          'lo que el sistema esperaba ese día. Si se pudiera editar, el historial ' +
          'dejaría de contar lo que pasó.',
      },
    ],
  },
  mediosPago: {
    titulo: 'Medios de pago',
    resumen: 'Con qué se puede cobrar, y qué pasa con cada uno después.',
    preguntas: [
      {
        pregunta: '¿Por qué el efectivo es distinto de los demás?',
        respuesta:
          'Porque es el único que queda en el cajón. La tarjeta, el QR y la ' +
          'transferencia van a una cuenta y acreditan días después, con la comisión ' +
          'ya descontada. Contarlos junto con el efectivo daría un arqueo que no ' +
          'cierra nunca.',
      },
      {
        pregunta: '¿Para qué cargo la comisión y los días?',
        respuesta:
          'Todavía no se usan, pero son los datos que después permiten cruzar lo que ' +
          'cobraste con lo que efectivamente te depositaron. Cargalos con los ' +
          'números de tu contrato: un valor inventado terminaría apareciendo en un ' +
          'reporte como si fuera real.',
      },
      {
        pregunta: '¿Puedo borrar un medio de pago que ya no uso?',
        respuesta:
          'No se borran: se desactivan. Dejan de aparecer al cobrar, pero los cobros ' +
          'viejos siguen sabiendo con qué se pagaron.',
      },
    ],
  },
} as const satisfies Record<string, AyudaPantalla>

/** Los nombres de pantalla que tienen ayuda escrita. */
export type ClaveAyuda = keyof typeof AYUDA
