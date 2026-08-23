/** Cuentas sobre las existencias que necesita más de una pantalla. */

import type { ExistenciaStock } from './tipos'

/**
 * Cuántas unidades hay de cada talle y color, sumando todos los locales.
 *
 * La pantalla de una prenda muestra un solo número por talle: es la respuesta
 * a "¿la tenés en M?", que en el mostrador quiere decir "¿la conseguís?" y no
 * "¿está en esta góndola?". El detalle local por local está en Existencias.
 */
export function totalPorVariante(existencias: ExistenciaStock[]): Map<string, number> {
  const total = new Map<string, number>()
  for (const fila of existencias) {
    total.set(fila.variante_id, (total.get(fila.variante_id) ?? 0) + fila.cantidad)
  }
  return total
}
