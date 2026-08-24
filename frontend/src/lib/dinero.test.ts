import { describe, expect, it } from 'vitest'

import { formatearPesos } from './dinero'

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
