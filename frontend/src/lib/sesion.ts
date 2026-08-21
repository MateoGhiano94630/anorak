/**
 * El token de la sesión vive en memoria y en ningún otro lado.
 *
 * Nada de localStorage ni sessionStorage: cualquier script que corra en la
 * página los lee, y el token es la llave de todo el sistema. El costo es que
 * al recargar la pestaña hay que volver a entrar; es un costo aceptable para
 * un sistema que se usa con la pestaña abierta toda la jornada.
 */

let token: string | null = null

/** Guarda el token de la sesión recién iniciada. */
export function guardarToken(nuevo: string): void {
  token = nuevo
}

/** Devuelve el token actual, o null si no hay sesión. */
export function leerToken(): string | null {
  return token
}

/** Borra el token. Se llama al salir y ante cualquier 401. */
export function limpiarToken(): void {
  token = null
}
