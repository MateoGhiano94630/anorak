/**
 * El signo de pregunta que abre la ayuda de la pantalla.
 *
 * El texto no está acá: sale de `lib/ayuda.ts`, que es la misma fuente con la
 * que se arma el manual de usuario. Así las dos no se pueden contradecir.
 */

import { useState } from 'react'

import { AYUDA, type ClaveAyuda } from '../lib/ayuda'

export function Ayuda({ pantalla }: { pantalla: ClaveAyuda }) {
  const [abierta, setAbierta] = useState(false)
  const contenido = AYUDA[pantalla]

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={() => setAbierta((estaba) => !estaba)}
        aria-expanded={abierta}
        className="inline-flex min-h-11 w-fit items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
      >
        <span
          aria-hidden="true"
          className="flex size-6 items-center justify-center rounded-full border border-slate-400 text-xs"
        >
          ?
        </span>
        {abierta ? 'Ocultar la ayuda' : '¿Cómo se usa esta pantalla?'}
      </button>

      {abierta ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-700">{contenido.resumen}</p>
          <dl className="mt-3 flex flex-col gap-3">
            {contenido.preguntas.map((item) => (
              <div key={item.pregunta}>
                <dt className="text-sm font-medium text-slate-900">{item.pregunta}</dt>
                <dd className="mt-1 text-sm text-slate-700">{item.respuesta}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
    </div>
  )
}
