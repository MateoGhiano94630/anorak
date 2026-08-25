/**
 * Las cuentas de una venta que se está armando.
 *
 * Están acá y no dentro de la pantalla porque son la parte que no puede estar
 * mal: un total mal sumado en el mostrador se cobra mal, y recién se descubre
 * en el arqueo del cierre.
 *
 * Los importes se manejan en centavos enteros. Sumar "0.1" + "0.2" en
 * JavaScript da 0.30000000000000004, y esa diferencia aparece sumada en un
 * cierre de caja.
 */

import type { LineaDelCarrito } from './tipos'

/** Convierte un importe escrito a centavos enteros. Cero si no es un número. */
export function aCentavos(importe: string | number | null | undefined): number {
  if (importe == null || importe === '') return 0
  const numero = typeof importe === 'number' ? importe : Number(importe)
  if (Number.isNaN(numero)) return 0
  return Math.round(numero * 100)
}

/** Convierte centavos enteros al texto con dos decimales que espera la API. */
export function aImporte(centavos: number): string {
  return (centavos / 100).toFixed(2)
}

/** Lo que suma una línea: cantidad por precio, menos su descuento. */
export function subtotalDeLinea(linea: LineaDelCarrito): number {
  const bruto = aCentavos(linea.precio_unitario) * linea.cantidad
  return bruto - aCentavos(linea.descuento)
}

export interface TotalesDelCarrito {
  /** La suma de las líneas, en centavos. */
  subtotal: number
  /** El descuento sobre el total, en centavos. */
  descuento: number
  /** Lo que hay que cobrar, en centavos. Nunca menor que cero. */
  total: number
}

/** Las tres cuentas de la venta que se está armando. */
export function totalesDelCarrito(
  lineas: LineaDelCarrito[],
  descuentoTotal: string,
): TotalesDelCarrito {
  const subtotal = lineas.reduce((suma, linea) => suma + subtotalDeLinea(linea), 0)
  const descuento = aCentavos(descuentoTotal)
  return { subtotal, descuento, total: Math.max(subtotal - descuento, 0) }
}

/** Lo que falta cobrar. Negativo quiere decir que se está cobrando de más. */
export function faltaCobrar(total: number, importes: string[]): number {
  const cobrado = importes.reduce((suma, importe) => suma + aCentavos(importe), 0)
  return total - cobrado
}

/**
 * El vuelto: lo que el cliente puso menos lo que se le cobra en efectivo.
 *
 * No se guarda en ningún lado. Lo que se registra es el importe de la venta,
 * no lo que el cliente puso sobre el mostrador.
 */
export function vuelto(entregado: string, cobradoEnEfectivo: string): number {
  return Math.max(aCentavos(entregado) - aCentavos(cobradoEnEfectivo), 0)
}
