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
    })
  } catch {
    // fetch solo rechaza por problemas de red, no por códigos de error.
    throw new ErrorApi('Sin conexión con el servidor.', 0)
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
