import { describe, expect, it } from 'vitest'

import { formatearPesos, formatearRango } from './dinero'

describe('formatearPesos', () => {
  it('muestra el importe en pesos con dos decimales', () => {
    // El espacio del formato argentino no es un espacio común, así que se
    // comparan las partes en vez de la cadena entera.
    const salida = formatearPesos('18500.55')
    expect(salida).toContain('18.500,55')
    expect(salida).toContain('$')
  })

  it('acepta el importe como texto, que es como llega del servidor', () => {
    // Los importes viajan como texto para no perder los centavos: convertirlos
    // a número en el navegador es lo que hace aparecer diferencias de un peso
    // en un cierre de caja.
    expect(formatearPesos('0.05')).toContain('0,05')
  })

  it('devuelve vacío cuando no hay importe', () => {
    expect(formatearPesos(null)).toBe('')
    expect(formatearPesos(undefined)).toBe('')
    expect(formatearPesos('')).toBe('')
  })
})

describe('formatearRango', () => {
  it('muestra un solo precio si todos los talles valen igual', () => {
    const salida = formatearRango('18500.00', '18500.00')
    expect(salida).not.toContain('–')
    expect(salida).toContain('18.500,00')
  })

  it('muestra los dos precios si algún talle vale distinto', () => {
    const salida = formatearRango('10000.00', '15000.00')
    expect(salida).toContain('10.000,00')
    expect(salida).toContain('15.000,00')
  })

  it('avisa cuando la prenda todavía no tiene precio', () => {
    expect(formatearRango(null, null)).toBe('Sin precio')
  })
})
