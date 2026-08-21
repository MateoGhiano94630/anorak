/** Los botones del sistema. */

import type { ButtonHTMLAttributes } from 'react'

type Variante = 'principal' | 'secundario' | 'peligro'

const ESTILOS: Record<Variante, string> = {
  principal: 'bg-slate-900 text-white hover:bg-slate-700',
  secundario: 'border border-slate-300 bg-white text-slate-900 hover:bg-slate-50',
  peligro: 'bg-red-700 text-white hover:bg-red-800',
}

type BotonProps = {
  variante?: Variante
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'>

export function Boton({ variante = 'principal', type = 'button', ...resto }: BotonProps) {
  return (
    <button
      type={type}
      // min-h-11: el alto mínimo para que un dedo acierte el botón sin ampliar
      // la pantalla. En el mostrador se usa apurado y con una mano.
      className={`inline-flex min-h-11 items-center justify-center rounded-lg px-4 text-base font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${ESTILOS[variante]}`}
      {...resto}
    />
  )
}
