/**
 * Preguntas sobre un importe que llega como texto.
 *
 * Los importes viajan como texto para no perder los centavos, así que
 * preguntarles el signo mirando si empiezan con un guion parece razonable y
 * no lo es: "-0.00" empieza con guion y no es una salida de plata. Estas dos
 * funciones existen para que esa comparación esté escrita en un solo lugar.
 */

/** True si el importe saca plata. */
export function esSalida(importe: string): boolean {
  return Number(importe) < 0
}

/** True si el importe es cero, venga escrito como venga. */
export function esCero(importe: string | null | undefined): boolean {
  if (importe == null || importe === '') return true
  return Number(importe) === 0
}
