/**
 * Formateo y lectura de fechas, todo en dd/mm/aaaa.
 *
 * Vive centralizado y no suelto en cada pantalla porque el formato tiene que
 * ser uno solo en todo el sistema: una fecha mostrada como 03/05 en una
 * pantalla y 05/03 en otra es un error de stock o de caja esperando a pasar.
 */

/** Separa una fecha sola (aaaa-mm-dd) en sus tres números. */
function partirFechaSola(texto: string): [number, number, number] | null {
  const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto)
  if (!partes) return null
  return [Number(partes[1]), Number(partes[2]), Number(partes[3])]
}

/**
 * Convierte lo que venga del servidor a un Date.
 *
 * Una fecha sola (aaaa-mm-dd) se arma en horario local a propósito: si se
 * pasara por `new Date('2026-03-05')`, JavaScript la lee como medianoche UTC
 * y en Argentina la muestra un día antes. Un cierre de caja fechado el día
 * anterior es una hora de alguien buscando la diferencia.
 */
export function aFecha(valor: string | Date | null | undefined): Date | null {
  if (valor == null || valor === '') return null
  if (valor instanceof Date) return Number.isNaN(valor.getTime()) ? null : valor
  const sola = partirFechaSola(valor)
  if (sola) return new Date(sola[0], sola[1] - 1, sola[2])
  const fecha = new Date(valor)
  return Number.isNaN(fecha.getTime()) ? null : fecha
}

/** Devuelve la fecha como dd/mm/aaaa. Cadena vacía si no hay fecha. */
export function formatearFecha(valor: string | Date | null | undefined): string {
  const fecha = aFecha(valor)
  if (!fecha) return ''
  const dia = String(fecha.getDate()).padStart(2, '0')
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  return `${dia}/${mes}/${fecha.getFullYear()}`
}

/** Devuelve la fecha con la hora, como dd/mm/aaaa hh:mm. */
export function formatearFechaHora(valor: string | Date | null | undefined): string {
  const fecha = aFecha(valor)
  if (!fecha) return ''
  const hora = String(fecha.getHours()).padStart(2, '0')
  const minutos = String(fecha.getMinutes()).padStart(2, '0')
  return `${formatearFecha(fecha)} ${hora}:${minutos}`
}

/** Convierte un dd/mm/aaaa escrito a mano en aaaa-mm-dd, o null si no es una fecha. */
export function aISO(texto: string): string | null {
  const partes = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(texto.trim())
  if (!partes) return null
  const dia = Number(partes[1])
  const mes = Number(partes[2])
  const anio = Number(partes[3])
  const fecha = new Date(anio, mes - 1, dia)
  // Rebota el 31/02: JavaScript lo acepta y lo corre al 3 de marzo en vez de
  // avisar que la fecha no existe.
  if (
    fecha.getFullYear() !== anio ||
    fecha.getMonth() !== mes - 1 ||
    fecha.getDate() !== dia
  ) {
    return null
  }
  return `${anio}-${String(mes).padStart(2, '0')}-${String(dia).padStart(2, '0')}`
}

/** Fecha de hoy en aaaa-mm-dd, según el reloj de la máquina. */
export function hoyISO(): string {
  const hoy = new Date()
  const mes = String(hoy.getMonth() + 1).padStart(2, '0')
  const dia = String(hoy.getDate()).padStart(2, '0')
  return `${hoy.getFullYear()}-${mes}-${dia}`
}
