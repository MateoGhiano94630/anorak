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
} as const satisfies Record<string, AyudaPantalla>

/** Los nombres de pantalla que tienen ayuda escrita. */
export type ClaveAyuda = keyof typeof AYUDA
