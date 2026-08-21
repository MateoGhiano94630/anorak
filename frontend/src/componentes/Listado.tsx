/**
 * Un listado que se dibuja como tabla en pantalla ancha y como tarjetas en
 * pantalla angosta, a partir de una sola definición de columnas.
 *
 * Existe porque el sistema se usa en la computadora del mostrador, en la
 * tablet del depósito y en el celular. Una `<table>` suelta en un celular
 * obliga a arrastrar la pantalla para los costados y la columna que importa
 * queda siempre fuera de la vista. Mantener dos listados en paralelo —uno de
 * tabla y otro de tarjetas— termina en que uno de los dos se olvida de
 * mostrar la columna nueva.
 */

import type { ReactNode } from 'react'

export interface Columna<T> {
  /** Identificador de la columna, único dentro del listado. */
  clave: string
  /** Encabezado de la tabla y rótulo dentro de la tarjeta. */
  titulo: string
  /** Lo que se muestra en la celda. */
  valor: (fila: T) => ReactNode
  /**
   * La columna que identifica la fila. En la tarjeta va arriba y en grande,
   * sin rótulo. Debería haber exactamente una por listado.
   */
  principal?: boolean
  /** Dato secundario: se muestra en la tabla y se omite en la tarjeta. */
  soloTabla?: boolean
  /** Importes y cantidades van a la derecha, para poder compararlos de un vistazo. */
  alDerecha?: boolean
}

export interface ListadoProps<T> {
  columnas: Columna<T>[]
  filas: T[]
  /** Devuelve un identificador estable de la fila. */
  claveDe: (fila: T) => string
  /** Qué decir cuando no hay nada que mostrar. */
  vacio: string
  /** Si se pasa, cada fila se puede tocar. */
  alTocarFila?: (fila: T) => void
  cargando?: boolean
}

export function Listado<T>({
  columnas,
  filas,
  claveDe,
  vacio,
  alTocarFila,
  cargando = false,
}: ListadoProps<T>) {
  if (cargando) {
    return <p className="py-8 text-center text-slate-500">Cargando…</p>
  }
  if (filas.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 py-10 text-center text-slate-500">
        {vacio}
      </p>
    )
  }

  const principal = columnas.find((columna) => columna.principal) ?? columnas[0]
  const enTarjeta = columnas.filter(
    (columna) => !columna.soloTabla && columna !== principal,
  )
  const tocable = alTocarFila !== undefined

  return (
    <>
      {/* Pantalla ancha: tabla. */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-slate-300">
              {columnas.map((columna) => (
                <th
                  key={columna.clave}
                  scope="col"
                  className={`px-3 py-2 font-medium text-slate-600 ${
                    columna.alDerecha ? 'text-right' : ''
                  }`}
                >
                  {columna.titulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filas.map((fila) => (
              <tr
                key={claveDe(fila)}
                onClick={tocable ? () => alTocarFila(fila) : undefined}
                className={`border-b border-slate-200 ${
                  tocable ? 'cursor-pointer hover:bg-slate-50' : ''
                }`}
              >
                {columnas.map((columna) => (
                  <td
                    key={columna.clave}
                    className={`px-3 py-2 ${columna.alDerecha ? 'text-right tabular-nums' : ''}`}
                  >
                    {columna.valor(fila)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pantalla angosta: una tarjeta por fila. */}
      <ul className="flex flex-col gap-3 md:hidden">
        {filas.map((fila) => (
          <li
            key={claveDe(fila)}
            onClick={tocable ? () => alTocarFila(fila) : undefined}
            className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${
              tocable ? 'cursor-pointer active:bg-slate-50' : ''
            }`}
          >
            <p className="text-base font-medium text-slate-900">
              {principal ? principal.valor(fila) : null}
            </p>
            <dl className="mt-2 flex flex-col gap-1 text-sm">
              {enTarjeta.map((columna) => (
                <div key={columna.clave} className="flex justify-between gap-4">
                  <dt className="text-slate-500">{columna.titulo}</dt>
                  <dd className="text-right text-slate-900">{columna.valor(fila)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </>
  )
}
