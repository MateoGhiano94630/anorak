/**
 * Cómo se nombra en pantalla lo que la API devuelve en mayúsculas.
 *
 * Está separado de los tipos porque es texto que lee una persona: "ADMIN" es
 * un valor guardado, "Administrador" es lo que va en la pantalla.
 */

import type { Rol } from './tipos'

export const NOMBRE_ROL: Record<Rol, string> = {
  ADMIN: 'Administrador',
  ENCARGADO: 'Encargado',
  VENDEDOR: 'Vendedor',
}

/** Arma las opciones de un selector a partir de una tabla de nombres. */
export function opcionesDe<T extends string>(
  nombres: Record<T, string>,
): { valor: string; texto: string }[] {
  return Object.entries(nombres).map(([valor, texto]) => ({
    valor,
    texto: texto as string,
  }))
}
