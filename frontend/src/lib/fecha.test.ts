import { describe, expect, it } from 'vitest'

import { aISO, formatearFecha, formatearFechaHora } from './fecha'

describe('formatearFecha', () => {
  it('muestra las fechas en dd/mm/aaaa', () => {
    expect(formatearFecha('2026-03-05')).toBe('05/03/2026')
  })

  it('no corre la fecha un día para atrás por la zona horaria', () => {
    // `new Date('2026-03-05')` se lee como medianoche UTC y en Argentina cae
    // el 4 de marzo. Es el error que hace que un cierre de caja aparezca
    // fechado el día anterior.
    expect(formatearFecha('2026-01-01')).toBe('01/01/2026')
    expect(formatearFecha('2026-12-31')).toBe('31/12/2026')
  })

  it('devuelve vacío cuando no hay fecha', () => {
    expect(formatearFecha(null)).toBe('')
    expect(formatearFecha(undefined)).toBe('')
    expect(formatearFecha('')).toBe('')
  })
})

describe('formatearFechaHora', () => {
  it('agrega la hora y los minutos', () => {
    expect(formatearFechaHora(new Date(2026, 2, 5, 9, 7))).toBe('05/03/2026 09:07')
  })
})

describe('aISO', () => {
  it('convierte lo que se escribe a mano', () => {
    expect(aISO('05/03/2026')).toBe('2026-03-05')
    expect(aISO('5/3/2026')).toBe('2026-03-05')
  })

  it('rechaza una fecha que no existe en vez de corrergirla sola', () => {
    // JavaScript acepta el 31 de febrero y lo mueve al 3 de marzo. Acá tiene
    // que avisar, no adivinar.
    expect(aISO('31/02/2026')).toBeNull()
    expect(aISO('32/01/2026')).toBeNull()
  })

  it('rechaza lo que no es una fecha', () => {
    expect(aISO('')).toBeNull()
    expect(aISO('mañana')).toBeNull()
    expect(aISO('05-03-2026')).toBeNull()
  })
})
