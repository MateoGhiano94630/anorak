/**
 * Elegir varias opciones de una lista, como casilleros grandes.
 *
 * Se usa para elegir los talles y los colores con los que armar las prendas.
 * Es una grilla de casilleros y no un `<select multiple>`: el nativo obliga a
 * mantener apretada una tecla para elegir más de uno, cosa que en una tablet
 * o un celular directamente no existe.
 */

export interface OpcionMultiple {
  valor: string
  texto: string
  /** Se muestra como un cuadradito de color al lado del texto. */
  colorHex?: string | null
}

interface SeleccionMultipleProps {
  etiqueta: string
  opciones: OpcionMultiple[]
  seleccionados: string[]
  alCambiar: (seleccionados: string[]) => void
  vacio?: string
}

export function SeleccionMultiple({
  etiqueta,
  opciones,
  seleccionados,
  alCambiar,
  vacio = 'No hay opciones cargadas.',
}: SeleccionMultipleProps) {
  function alternar(valor: string): void {
    alCambiar(
      seleccionados.includes(valor)
        ? seleccionados.filter((elegido) => elegido !== valor)
        : [...seleccionados, valor],
    )
  }

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-medium text-slate-700">{etiqueta}</legend>
      {opciones.length === 0 ? (
        <p className="text-sm text-slate-500">{vacio}</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {opciones.map((opcion) => {
            const elegido = seleccionados.includes(opcion.valor)
            return (
              <label
                key={opcion.valor}
                className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border px-3 text-base ${
                  elegido
                    ? 'border-slate-900 bg-slate-900 text-white'
                    : 'border-slate-300 bg-white text-slate-700'
                }`}
              >
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={elegido}
                  onChange={() => {
                    alternar(opcion.valor)
                  }}
                />
                {opcion.colorHex != null ? (
                  <span
                    aria-hidden="true"
                    style={{ backgroundColor: opcion.colorHex }}
                    className="size-4 rounded-full border border-slate-400"
                  />
                ) : null}
                {opcion.texto}
              </label>
            )
          })}
        </div>
      )}
    </fieldset>
  )
}
