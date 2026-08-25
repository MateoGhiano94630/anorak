/**
 * Cómo se nombra en pantalla lo que la API devuelve en mayúsculas.
 *
 * Está separado de los tipos porque es texto que lee una persona: "ADMIN" es
 * un valor guardado, "Administrador" es lo que va en la pantalla.
 */

import type { EstadoVenta, Rol, TipoMedioPago, TipoMovimientoCaja } from './tipos'

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

/**
 * Cómo se nombra cada movimiento de caja en pantalla.
 *
 * "Mercadería que llegó" y no "INGRESO": quien atiende el local no tiene por
 * qué traducir la palabra que el sistema guarda.
 */
export const NOMBRE_MOVIMIENTO_CAJA: Record<TipoMovimientoCaja, string> = {
  APERTURA: 'Fondo de apertura',
  COBRO: 'Cobro de una venta',
  INGRESO: 'Plata que se agregó',
  RETIRO: 'Plata que se sacó',
  GASTO: 'Gasto pagado de la caja',
  DEVOLUCION: 'Devolución',
  DIFERENCIA: 'Diferencia del arqueo',
  CIERRE: 'Retiro del cierre',
}

/** Los tres movimientos que una persona carga a mano. */
export const MOVIMIENTOS_A_MANO = {
  INGRESO: 'Agregar plata a la caja',
  RETIRO: 'Sacar plata de la caja',
  GASTO: 'Pagar un gasto de la caja',
} as const

export const NOMBRE_MEDIO_PAGO: Record<TipoMedioPago, string> = {
  EFECTIVO: 'Efectivo',
  TARJETA_DEBITO: 'Tarjeta de débito',
  TARJETA_CREDITO: 'Tarjeta de crédito',
  QR: 'QR o billetera',
  TRANSFERENCIA: 'Transferencia',
}

export const NOMBRE_ESTADO_VENTA: Record<EstadoVenta, string> = {
  REGISTRADA: 'Registrada',
  ANULADA: 'Anulada',
}
