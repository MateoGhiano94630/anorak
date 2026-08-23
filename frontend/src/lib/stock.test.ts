import { describe, expect, it } from 'vitest'

import { totalPorVariante } from './stock'
import type { ExistenciaStock } from './tipos'

function existencia(
  variante_id: string,
  sucursal: string,
  cantidad: number,
): ExistenciaStock {
  return {
    variante_id,
    sucursal_id: sucursal,
    sucursal,
    producto_id: 'p1',
    producto: 'Remera lisa',
    talle: 'M',
    color: 'Negro',
    sku: 'NIKREMLIS-M-NEG',
    cantidad,
    stock_minimo: 0,
    bajo_minimo: false,
  }
}

describe('totalPorVariante', () => {
  it('suma lo que hay del mismo talle en locales distintos', () => {
    // "¿La tenés en M?" en el mostrador quiere decir "¿la conseguís?", no
    // "¿está en esta góndola?".
    const total = totalPorVariante([
      existencia('v1', 'centro', 4),
      existencia('v1', 'norte', 9),
    ])
    expect(total.get('v1')).toBe(13)
  })

  it('no mezcla talles distintos', () => {
    const total = totalPorVariante([
      existencia('v1', 'centro', 4),
      existencia('v2', 'centro', 7),
    ])
    expect(total.get('v1')).toBe(4)
    expect(total.get('v2')).toBe(7)
  })

  it('un talle sin existencias no aparece', () => {
    // La pantalla lo muestra como cero: la ausencia de fila y el cero son lo
    // mismo para quien atiende.
    expect(totalPorVariante([]).get('v1')).toBeUndefined()
  })
})
