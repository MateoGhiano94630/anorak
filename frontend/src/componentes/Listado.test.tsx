import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Listado, type Columna } from './Listado'

interface Prenda {
  id: string
  nombre: string
  talle: string
  proveedor: string
}

const COLUMNAS: Columna<Prenda>[] = [
  { clave: 'nombre', titulo: 'Prenda', valor: (p) => p.nombre, principal: true },
  { clave: 'talle', titulo: 'Talle', valor: (p) => p.talle },
  { clave: 'prov', titulo: 'Proveedor', valor: (p) => p.proveedor, soloTabla: true },
]

const FILAS: Prenda[] = [
  { id: '1', nombre: 'Remera lisa', talle: 'M', proveedor: 'Textil Sur' },
]

function armar(filas: Prenda[] = FILAS) {
  return render(
    <Listado
      columnas={COLUMNAS}
      filas={filas}
      claveDe={(fila) => fila.id}
      vacio="No hay prendas cargadas."
    />,
  )
}

describe('Listado', () => {
  it('dibuja la tabla y las tarjetas desde la misma definición', () => {
    armar()
    // Una vez en la tabla y otra en la tarjeta: las dos formas salen de la
    // misma lista de columnas, así que no pueden quedar desincronizadas.
    expect(screen.getAllByText('Remera lisa')).toHaveLength(2)
    expect(screen.getAllByText('M')).toHaveLength(2)
  })

  it('deja fuera de la tarjeta las columnas marcadas como soloTabla', () => {
    armar()
    expect(screen.getAllByText('Textil Sur')).toHaveLength(1)
  })

  it('avisa cuando no hay nada, con el texto de la pantalla', () => {
    armar([])
    expect(screen.getByText('No hay prendas cargadas.')).toBeInTheDocument()
  })
})
