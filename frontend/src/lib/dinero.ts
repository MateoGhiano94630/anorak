/**
 * Presentación de importes en pesos.
 *
 * Los importes viajan desde el servidor como texto ("12345.67") y no como
 * número: los decimales de JavaScript no representan exactamente los
 * centavos, y en un cierre de caja esa diferencia aparece. Acá solo se
 * formatean para mostrar; ninguna cuenta de plata se hace en el navegador.
 */

const FORMATO = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  minimumFractionDigits: 2,
})

/** Devuelve el importe listo para mostrar, por ejemplo "$ 12.345,67". */
export function formatearPesos(valor: string | number | null | undefined): string {
  if (valor == null || valor === '') return ''
  const numero = typeof valor === 'number' ? valor : Number(valor)
  if (Number.isNaN(numero)) return ''
  return FORMATO.format(numero)
}

/**
 * El precio de una prenda que puede valer distinto según el talle.
 *
 * Si todos los talles valen lo mismo se muestra un solo importe: un rango con
 * los dos números iguales se lee como si hubiera dos precios distintos y hace
 * dudar a quien atiende.
 */
export function formatearRango(
  desde: string | null,
  hasta: string | null,
  sinPrecio = 'Sin precio',
): string {
  if (desde === null) return sinPrecio
  if (hasta === null || desde === hasta) return formatearPesos(desde)
  return `${formatearPesos(desde)} – ${formatearPesos(hasta)}`
}
