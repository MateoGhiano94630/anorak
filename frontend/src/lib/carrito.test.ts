import { describe, expect, it } from 'vitest'

import {
  aCentavos,
  aImporte,
  faltaCobrar,
  subtotalDeLinea,
  totalesDelCarrito,
  vuelto,
} from './carrito'
import type { LineaDelCarrito } from './tipos'

function linea(campos: Partial<LineaDelCarrito>): LineaDelCarrito {
  return {
    clave: '1',
    articulo_id: null,
    descripcion: 'Campera',
    talle: '',
    cantidad: 1,
    precio_unitario: '0',
    descuento: '0',
    ...campos,
  }
}

describe('aCentavos', () => {
  it('no pierde los centavos al convertir', () => {
    expect(aCentavos('18500.55')).toBe(1850055)
    expect(aCentavos('0.05')).toBe(5)
  })

  it('un campo vacío o mal escrito vale cero', () => {
    expect(aCentavos('')).toBe(0)
    expect(aCentavos(null)).toBe(0)
    expect(aCentavos('cualquier cosa')).toBe(0)
  })
})

describe('las cuentas se hacen en centavos enteros', () => {
  it('no arrastra el error de los decimales de JavaScript', () => {
    // Sumando en pesos, 0.1 + 0.2 da 0.30000000000000004. Ese centavo de más
    // aparece sumado en el arqueo del cierre.
    const totales = totalesDelCarrito(
      [
        linea({ clave: 'a', precio_unitario: '0.10' }),
        linea({ clave: 'b', precio_unitario: '0.20' }),
      ],
      '0',
    )
    expect(aImporte(totales.total)).toBe('0.30')
  })
})

describe('subtotalDeLinea', () => {
  it('multiplica por la cantidad', () => {
    expect(subtotalDeLinea(linea({ cantidad: 3, precio_unitario: '25000.00' }))).toBe(
      7500000,
    )
  })

  it('resta el descuento de la línea', () => {
    expect(
      subtotalDeLinea(
        linea({ cantidad: 1, precio_unitario: '100000.00', descuento: '15000.00' }),
      ),
    ).toBe(8500000)
  })
})

describe('totalesDelCarrito', () => {
  it('resta el descuento del total', () => {
    const totales = totalesDelCarrito(
      [linea({ cantidad: 2, precio_unitario: '25000.00' })],
      '5000.00',
    )
    expect(aImporte(totales.subtotal)).toBe('50000.00')
    expect(aImporte(totales.total)).toBe('45000.00')
  })

  it('un descuento mayor que la venta no deja el total en negativo', () => {
    const totales = totalesDelCarrito(
      [linea({ precio_unitario: '10000.00' })],
      '99999.00',
    )
    expect(totales.total).toBe(0)
  })
})

describe('faltaCobrar', () => {
  it('dice cuánto falta cuando se cobró de menos', () => {
    expect(aImporte(faltaCobrar(10000000, ['40000.00']))).toBe('60000.00')
  })

  it('da negativo cuando se está cobrando de más', () => {
    expect(faltaCobrar(10000000, ['150000.00'])).toBeLessThan(0)
  })

  it('da cero cuando la venta está cubierta con varios medios', () => {
    expect(faltaCobrar(10000000, ['40000.00', '60000.00'])).toBe(0)
  })
})

describe('vuelto', () => {
  it('es lo que el cliente puso menos lo que se le cobra', () => {
    expect(aImporte(vuelto('100000.00', '85500.00'))).toBe('14500.00')
  })

  it('nunca es negativo', () => {
    // Si entregó menos de lo que hay que cobrar, no hay vuelto: falta plata.
    expect(vuelto('50000.00', '85500.00')).toBe(0)
  })
})
