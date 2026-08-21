/**
 * Cómo se nombra en pantalla lo que la API devuelve en mayúsculas.
 *
 * Está separado de los tipos porque es texto que lee una persona: "NINO" es
 * un valor guardado, "Niño" es lo que va en la pantalla.
 */

import type { Genero, Rol, Temporada, TipoSucursal } from './tipos'

export const NOMBRE_GENERO: Record<Genero, string> = {
  HOMBRE: 'Hombre',
  MUJER: 'Mujer',
  UNISEX: 'Unisex',
  NINO: 'Niño',
  NINA: 'Niña',
  BEBE: 'Bebé',
}

export const NOMBRE_TEMPORADA: Record<Temporada, string> = {
  VERANO: 'Verano',
  INVIERNO: 'Invierno',
  ENTRETIEMPO: 'Entretiempo',
  ATEMPORAL: 'Todo el año',
}

export const NOMBRE_ROL: Record<Rol, string> = {
  ADMIN: 'Administrador',
  ENCARGADO: 'Encargado',
  VENDEDOR: 'Vendedor',
}

export const NOMBRE_TIPO_SUCURSAL: Record<TipoSucursal, string> = {
  LOCAL: 'Local',
  DEPOSITO: 'Depósito',
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
