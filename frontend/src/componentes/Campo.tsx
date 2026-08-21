/**
 * Los controles de carga del sistema.
 *
 * Están juntos y se usan siempre estos, en lugar de un `<input>` suelto por
 * pantalla, por una razón concreta: la letra de un campo de carga nunca puede
 * bajar de 16px. Si baja, iPhone hace zoom solo al tocarlo y descoloca la
 * pantalla; quien está cobrando tiene que salir del zoom a mano en cada campo.
 * `text-base` de Tailwind son exactamente esos 16px.
 */

import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'
import { useId } from 'react'

const CLASES_CONTROL =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base ' +
  'text-slate-900 outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 ' +
  'disabled:bg-slate-100 disabled:text-slate-500'

interface EnvoltorioProps {
  etiqueta: string
  id: string
  ayuda?: string
  error?: string
  children: ReactNode
}

function Envoltorio({ etiqueta, id, ayuda, error, children }: EnvoltorioProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-slate-700">
        {etiqueta}
      </label>
      {children}
      {ayuda !== undefined && !error ? (
        <p className="text-xs text-slate-500">{ayuda}</p>
      ) : null}
      {error !== undefined ? (
        <p className="text-xs text-red-700" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}

type CampoProps = {
  etiqueta: string
  ayuda?: string
  error?: string
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'className' | 'id'>

/** Campo de carga de una línea. */
export function Campo({ etiqueta, ayuda, error, ...resto }: CampoProps) {
  const id = useId()
  return (
    <Envoltorio etiqueta={etiqueta} id={id} ayuda={ayuda} error={error}>
      <input id={id} className={CLASES_CONTROL} {...resto} />
    </Envoltorio>
  )
}

type SelectorProps = {
  etiqueta: string
  ayuda?: string
  error?: string
  opciones: { valor: string; texto: string }[]
} & Omit<SelectHTMLAttributes<HTMLSelectElement>, 'className' | 'id'>

/** Selector de una opción entre varias. */
export function Selector({ etiqueta, ayuda, error, opciones, ...resto }: SelectorProps) {
  const id = useId()
  return (
    <Envoltorio etiqueta={etiqueta} id={id} ayuda={ayuda} error={error}>
      <select id={id} className={CLASES_CONTROL} {...resto}>
        {opciones.map((opcion) => (
          <option key={opcion.valor} value={opcion.valor}>
            {opcion.texto}
          </option>
        ))}
      </select>
    </Envoltorio>
  )
}

export { CLASES_CONTROL, Envoltorio }
