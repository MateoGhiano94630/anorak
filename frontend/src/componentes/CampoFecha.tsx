/**
 * Carga de fechas en dd/mm/aaaa.
 *
 * No usa `<input type="date">` a propósito. Ese control lo dibuja el navegador
 * con el formato de la configuración de la máquina, no con el del sistema: en
 * una computadora con Windows en inglés, la misma pantalla que muestra
 * 05/03/2026 en el listado pide la fecha como 03/05/2026. Nadie lo nota hasta
 * que un movimiento queda fechado dos meses después.
 */

import { useId, useState } from 'react'

import { aISO, formatearFecha } from '../lib/fecha'
import { CLASES_CONTROL, Envoltorio } from './Campo'

interface CampoFechaProps {
  etiqueta: string
  /** La fecha, en aaaa-mm-dd. Cadena vacía si no hay ninguna. */
  valor: string
  /** Recibe la fecha en aaaa-mm-dd, o cadena vacía si se borró. */
  alCambiar: (valorISO: string) => void
  ayuda?: string
  requerido?: boolean
  disabled?: boolean
}

/** Deja escribir de corrido: al llegar al día y al mes pone la barra sola. */
function conBarras(texto: string): string {
  const numeros = texto.replace(/\D/g, '').slice(0, 8)
  const partes = [numeros.slice(0, 2), numeros.slice(2, 4), numeros.slice(4, 8)]
  return partes.filter((parte) => parte !== '').join('/')
}

export function CampoFecha({
  etiqueta,
  valor,
  alCambiar,
  ayuda,
  requerido = false,
  disabled = false,
}: CampoFechaProps) {
  const id = useId()
  const [texto, setTexto] = useState(() => formatearFecha(valor))

  // Cuando la fecha cambia desde afuera (se cargó un formulario para editar,
  // se limpió un filtro) hay que redibujar lo escrito. Se hace comparando
  // contra el valor anterior durante el dibujado y no con un `useEffect`:
  // el efecto provoca un segundo dibujado con el dato viejo en pantalla.
  const [valorPrevio, setValorPrevio] = useState(valor)
  if (valor !== valorPrevio) {
    setValorPrevio(valor)
    setTexto(formatearFecha(valor))
  }

  const incompleta = texto.length > 0 && texto.length < 10
  const invalida = texto.length === 10 && aISO(texto) === null

  function manejarCambio(nuevo: string): void {
    const conFormato = conBarras(nuevo)
    setTexto(conFormato)
    if (conFormato === '') {
      alCambiar('')
      return
    }
    const iso = aISO(conFormato)
    if (iso !== null) alCambiar(iso)
  }

  let error: string | undefined
  if (invalida) error = 'Esa fecha no existe. Revisá el día y el mes.'
  else if (incompleta) error = 'Escribí la fecha completa, como 05/03/2026.'

  return (
    <Envoltorio etiqueta={etiqueta} id={id} ayuda={ayuda} error={error}>
      <input
        id={id}
        // `inputMode` numérico levanta el teclado de números en el celular sin
        // volver el campo un `type="number"`, que no acepta las barras.
        inputMode="numeric"
        autoComplete="off"
        placeholder="dd/mm/aaaa"
        maxLength={10}
        required={requerido}
        disabled={disabled}
        value={texto}
        onChange={(evento) => manejarCambio(evento.target.value)}
        className={CLASES_CONTROL}
      />
    </Envoltorio>
  )
}
