/**
 * Único punto por el que el sistema le habla al servidor.
 *
 * Centralizado para que el token, el manejo de errores y el cierre de sesión
 * ante un 401 estén escritos una sola vez. Una pantalla que llame a `fetch`
 * por su cuenta es una pantalla que algún día se olvida de alguna de las tres.
 */

import { leerToken, limpiarToken } from './sesion'

const BASE = import.meta.env.VITE_API_URL ?? '/api'

/** Error con el mensaje que el servidor quiso mostrarle a la persona. */
export class ErrorApi extends Error {
  readonly estado: number

  constructor(mensaje: string, estado: number) {
    super(mensaje)
    this.name = 'ErrorApi'
    this.estado = estado
  }
}

/** Se dispara cuando el servidor rechaza el token: la sesión terminó. */
export const EVENTO_SESION_VENCIDA = 'anorak:sesion-vencida'

/**
 * Cuánto se espera una respuesta antes de darla por perdida.
 *
 * Sin esto, `fetch` espera para siempre: si el servidor se quedó pensando, la
 * pantalla se queda con el spinner girando y nadie se entera nunca de nada.
 * Media hora de mostrador se puede perder así, mirando una rueda.
 *
 * Treinta segundos es largo a propósito. Un servidor que estuvo dormido tarda
 * en despertarse, y cortarlo antes de tiempo convertiría una demora en un
 * error. Pasado ese rato ya no es demora: algo se rompió, y quien está
 * atendiendo necesita que se lo digan para poder reintentar.
 */
const ESPERA_MAXIMA_MS = 30_000

/** Subir un archivo es más lento que pedir un dato: viaja el archivo entero. */
const ESPERA_MAXIMA_SUBIDA_MS = 60_000

/** Traduce la falla de `fetch` al mensaje que corresponde. */
function errorDeRed(error: unknown): ErrorApi {
  // `AbortSignal.timeout` aborta con un DOMException llamado 'TimeoutError'.
  // Distinguirlo importa: "sin conexión" manda a revisar el wifi del local, y
  // acá el wifi puede estar perfecto y el problema estar del otro lado.
  if (error instanceof DOMException && error.name === 'TimeoutError') {
    return new ErrorApi('El servidor tardó demasiado en responder. Probá de nuevo.', 0)
  }
  return new ErrorApi('Sin conexión con el servidor.', 0)
}

interface Opciones {
  metodo?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  cuerpo?: unknown
  /** Para el ingreso, que todavía no tiene token. */
  sinSesion?: boolean
}

async function mensajeDeError(respuesta: Response): Promise<string> {
  try {
    const cuerpo: unknown = await respuesta.json()
    if (cuerpo && typeof cuerpo === 'object' && 'detail' in cuerpo) {
      const detalle: unknown = cuerpo.detail
      if (typeof detalle === 'string') return detalle
      // Los errores de validación de FastAPI vienen como lista.
      if (Array.isArray(detalle) && detalle.length > 0) {
        const primero: unknown = detalle[0]
        if (primero && typeof primero === 'object' && 'msg' in primero) {
          return String(primero.msg)
        }
      }
    }
  } catch {
    // El cuerpo no era JSON: se cae al mensaje genérico de abajo.
  }
  return 'No se pudo completar la operación. Probá de nuevo.'
}

/** Llama a la API y devuelve la respuesta ya convertida. */
export async function pedir<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  const cabeceras: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = leerToken()
  if (token && !opciones.sinSesion) cabeceras['Authorization'] = `Bearer ${token}`

  let respuesta: Response
  try {
    respuesta = await fetch(`${BASE}${ruta}`, {
      method: opciones.metodo ?? 'GET',
      headers: cabeceras,
      body: opciones.cuerpo === undefined ? null : JSON.stringify(opciones.cuerpo),
      signal: AbortSignal.timeout(ESPERA_MAXIMA_MS),
    })
  } catch (error) {
    // fetch solo rechaza por problemas de red, no por códigos de error.
    throw errorDeRed(error)
  }

  if (respuesta.status === 401 && !opciones.sinSesion) {
    limpiarToken()
    window.dispatchEvent(new CustomEvent(EVENTO_SESION_VENCIDA))
    throw new ErrorApi('Tu sesión terminó. Volvé a entrar.', 401)
  }
  if (!respuesta.ok) {
    throw new ErrorApi(await mensajeDeError(respuesta), respuesta.status)
  }
  if (respuesta.status === 204) return undefined as T
  return (await respuesta.json()) as T
}

/** Sube un archivo. Va aparte de `pedir` porque no lleva JSON sino un formulario.
 *
 * No se le pone `Content-Type` a mano a propósito: el navegador lo arma solo
 * con el separador que necesita el formulario. Poniéndolo, el servidor recibe
 * un cuerpo que no puede leer.
 */
export async function subirArchivo<T>(ruta: string, archivo: File): Promise<T> {
  const formulario = new FormData()
  formulario.append('archivo', archivo)

  const cabeceras: Record<string, string> = {}
  const token = leerToken()
  if (token) cabeceras['Authorization'] = `Bearer ${token}`

  let respuesta: Response
  try {
    respuesta = await fetch(`${BASE}${ruta}`, {
      method: 'POST',
      headers: cabeceras,
      body: formulario,
      signal: AbortSignal.timeout(ESPERA_MAXIMA_SUBIDA_MS),
    })
  } catch (error) {
    throw errorDeRed(error)
  }

  if (respuesta.status === 401) {
    limpiarToken()
    window.dispatchEvent(new CustomEvent(EVENTO_SESION_VENCIDA))
    throw new ErrorApi('Tu sesión terminó. Volvé a entrar.', 401)
  }
  if (!respuesta.ok) {
    throw new ErrorApi(await mensajeDeError(respuesta), respuesta.status)
  }
  return (await respuesta.json()) as T
}
