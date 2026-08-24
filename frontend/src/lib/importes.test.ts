import { describe, expect, it } from 'vitest'

import { esCero, esSalida } from './importes'

describe('esSalida', () => {
  it('reconoce lo que saca plata del cajón', () => {
    expect(esSalida('-8000.00')).toBe(true)
    expect(esSalida('8000.00')).toBe(false)
  })

  it('no toma "-0.00" como una salida', () => {
    // Es la razón de que esto no sea `importe.startsWith('-')`: un cero con
    // signo se dibujaría en rojo como si hubiera salido plata.
    expect(esSalida('-0.00')).toBe(false)
  })
})

describe('esCero', () => {
  it('reconoce el cero escrito de varias formas', () => {
    expect(esCero('0')).toBe(true)
    expect(esCero('0.00')).toBe(true)
    expect(esCero('-0.00')).toBe(true)
  })

  it('un arqueo sin cerrar no tiene diferencia', () => {
    expect(esCero(null)).toBe(true)
  })

  it('una diferencia real no es cero', () => {
    expect(esCero('-500.00')).toBe(false)
    expect(esCero('0.01')).toBe(false)
  })
})
