import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { SeleccionMultiple } from './SeleccionMultiple'

function Prueba() {
  const [elegidos, setElegidos] = useState<string[]>([])
  return (
    <>
      <SeleccionMultiple
        etiqueta="Talles"
        opciones={[
          { valor: 's', texto: 'S' },
          { valor: 'm', texto: 'M' },
          { valor: 'l', texto: 'L' },
        ]}
        seleccionados={elegidos}
        alCambiar={setElegidos}
      />
      <p>Elegidos: {elegidos.join(',')}</p>
    </>
  )
}

describe('SeleccionMultiple', () => {
  it('deja elegir varias opciones sin teclas de por medio', async () => {
    // Es la razón de existir del componente: un `select multiple` obliga a
    // mantener apretada una tecla, cosa que en una tablet no existe.
    const usuario = userEvent.setup()
    render(<Prueba />)

    await usuario.click(screen.getByText('S'))
    await usuario.click(screen.getByText('L'))

    expect(screen.getByText('Elegidos: s,l')).toBeInTheDocument()
  })

  it('vuelve a tocar una opción para sacarla', async () => {
    const usuario = userEvent.setup()
    render(<Prueba />)

    await usuario.click(screen.getByText('M'))
    await usuario.click(screen.getByText('M'))

    expect(screen.getByText('Elegidos:')).toBeInTheDocument()
  })

  it('avisa cuando no hay nada para elegir', () => {
    render(
      <SeleccionMultiple
        etiqueta="Colores"
        opciones={[]}
        seleccionados={[]}
        alCambiar={() => undefined}
        vacio="Todavía no hay colores cargados."
      />,
    )
    expect(screen.getByText('Todavía no hay colores cargados.')).toBeInTheDocument()
  })
})
