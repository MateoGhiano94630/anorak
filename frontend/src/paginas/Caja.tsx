/** La caja del día: abrir, registrar movimientos y cerrar. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo, Selector } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { useSesion } from '../contexto/sesion'
import { ErrorApi, pedir } from '../lib/api'
import { formatearPesos } from '../lib/dinero'
import { esCero, esSalida } from '../lib/importes'
import { MOVIMIENTOS_A_MANO, NOMBRE_MOVIMIENTO_CAJA } from '../lib/etiquetas'
import { formatearFechaHora } from '../lib/fecha'
import type { SesionCaja, TipoMovimientoManual } from '../lib/tipos'

const COLUMNAS: Columna<SesionCaja['movimientos'][number]>[] = [
  {
    clave: 'que',
    titulo: 'Qué pasó',
    principal: true,
    valor: (m) => (
      <span>
        {NOMBRE_MOVIMIENTO_CAJA[m.tipo]}
        {m.concepto !== null ? (
          <span className="text-slate-500"> · {m.concepto}</span>
        ) : null}
      </span>
    ),
  },
  { clave: 'medio', titulo: 'Medio', valor: (m) => m.medio_pago, soloTabla: true },
  {
    clave: 'importe',
    titulo: 'Importe',
    alDerecha: true,
    valor: (m) => (
      <span className={esSalida(m.importe) ? 'text-red-700' : 'text-green-800'}>
        {formatearPesos(m.importe)}
      </span>
    ),
  },
  {
    clave: 'comprobante',
    titulo: 'Comprobante',
    valor: (m) => m.comprobante ?? '—',
    soloTabla: true,
  },
  {
    clave: 'fecha',
    titulo: 'Cuándo',
    valor: (m) => formatearFechaHora(m.fecha),
    soloTabla: true,
  },
]

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-medium text-slate-900">{titulo}</h2>
      {children}
    </section>
  )
}

export function Caja() {
  const clienteConsultas = useQueryClient()
  const { usuario } = useSesion()
  const puedeVerHistorial = usuario?.rol === 'ADMIN' || usuario?.rol === 'ENCARGADO'
  const [error, setError] = useState<string | null>(null)

  const caja = useQuery({
    queryKey: ['caja'],
    queryFn: () => pedir<SesionCaja | null>('/caja/actual'),
  })

  function refrescar(): void {
    setError(null)
    void clienteConsultas.invalidateQueries({ queryKey: ['caja'] })
    void clienteConsultas.invalidateQueries({ queryKey: ['sesiones-caja'] })
  }

  function avisar(fallo: unknown): void {
    setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo completar.')
  }

  if (caja.isPending) return <p className="text-slate-500">Cargando…</p>

  const sesion = caja.data ?? null

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Caja</h1>
        {puedeVerHistorial ? (
          <Link to="/caja/cierres" className="text-sm text-slate-600 underline">
            Ver los cierres anteriores
          </Link>
        ) : null}
      </div>

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      {sesion === null ? (
        <Apertura alAbrir={refrescar} alFallar={avisar} />
      ) : (
        <>
          <Seccion titulo="La caja está abierta">
            <dl className="grid gap-3 sm:grid-cols-3">
              <div>
                <dt className="text-sm text-slate-500">La abrió</dt>
                <dd className="text-base">{sesion.abierta_por_nombre ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">Desde</dt>
                <dd className="text-base">{formatearFechaHora(sesion.fecha_apertura)}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">Fondo de apertura</dt>
                <dd className="text-base">{formatearPesos(sesion.monto_inicial)}</dd>
              </div>
            </dl>

            {sesion.totales_por_medio.length > 0 ? (
              <div>
                <p className="text-sm font-medium text-slate-700">
                  Cobrado con otros medios
                </p>
                <p className="text-xs text-slate-500">
                  No están en el cajón: acreditan en la cuenta. Sirven para cruzar contra
                  el cierre del posnet.
                </p>
                <ul className="mt-2 flex flex-col gap-1 text-sm">
                  {sesion.totales_por_medio.map((total) => (
                    <li key={total.medio_pago_id} className="flex justify-between gap-4">
                      <span className="text-slate-600">{total.medio_pago}</span>
                      <span className="tabular-nums">{formatearPesos(total.total)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </Seccion>

          <MovimientoNuevo alGuardar={refrescar} alFallar={avisar} />

          <Seccion titulo="Movimientos del día">
            <Listado
              columnas={COLUMNAS}
              filas={sesion.movimientos}
              claveDe={(m) => m.id}
              vacio="Todavía no se movió nada."
            />
          </Seccion>

          <Cierre alCerrar={refrescar} alFallar={avisar} />
        </>
      )}

      <Ayuda pantalla="caja" />
    </div>
  )
}

/** Formulario de apertura, con el fondo que propone el sistema. */
function Apertura({
  alAbrir,
  alFallar,
}: {
  alAbrir: () => void
  alFallar: (fallo: unknown) => void
}) {
  const sugerido = useQuery({
    queryKey: ['fondo-sugerido'],
    queryFn: () => pedir<{ fondo_sugerido: string }>('/caja/fondo-sugerido'),
  })
  const [monto, setMonto] = useState('')
  const [tocado, setTocado] = useState(false)

  // El sugerido se carga una vez y después manda lo que la persona escriba.
  const valor = tocado ? monto : (sugerido.data?.fondo_sugerido ?? '')

  const abrir = useMutation({
    mutationFn: () =>
      pedir<SesionCaja>('/caja/apertura', {
        metodo: 'POST',
        cuerpo: { monto_inicial: valor },
      }),
    onSuccess: alAbrir,
    onError: alFallar,
  })

  return (
    <Seccion titulo="La caja está cerrada">
      <p className="text-sm text-slate-600">
        Contá el efectivo que hay en el cajón para dar vuelto y abrila. Ese número es el
        punto de partida del arqueo de hoy.
      </p>
      <form
        onSubmit={(evento) => {
          evento.preventDefault()
          abrir.mutate()
        }}
        className="flex flex-col gap-4 sm:flex-row sm:items-end"
      >
        <div className="sm:w-64">
          <Campo
            etiqueta="Efectivo en el cajón"
            inputMode="decimal"
            required
            placeholder="0.00"
            ayuda="El sistema propone el de siempre. Corregilo si contaste otra cosa."
            value={valor}
            onChange={(evento) => {
              setTocado(true)
              setMonto(evento.target.value)
            }}
          />
        </div>
        <Boton type="submit" disabled={abrir.isPending || valor === ''}>
          Abrir la caja
        </Boton>
      </form>
    </Seccion>
  )
}

/** Carga de un ingreso, un retiro o un gasto. */
function MovimientoNuevo({
  alGuardar,
  alFallar,
}: {
  alGuardar: () => void
  alFallar: (fallo: unknown) => void
}) {
  const [tipo, setTipo] = useState<TipoMovimientoManual>('RETIRO')
  const [importe, setImporte] = useState('')
  const [concepto, setConcepto] = useState('')
  const [comprobante, setComprobante] = useState('')

  const registrar = useMutation({
    mutationFn: () =>
      pedir<SesionCaja>('/caja/movimientos', {
        metodo: 'POST',
        cuerpo: {
          tipo,
          importe,
          concepto,
          comprobante: comprobante === '' ? null : comprobante,
        },
      }),
    onSuccess: () => {
      setImporte('')
      setConcepto('')
      setComprobante('')
      alGuardar()
    },
    onError: alFallar,
  })

  return (
    <Seccion titulo="Registrar un movimiento">
      <form
        onSubmit={(evento) => {
          evento.preventDefault()
          registrar.mutate()
        }}
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5"
      >
        <Selector
          etiqueta="Qué estás haciendo"
          value={tipo}
          onChange={(evento) => setTipo(evento.target.value as TipoMovimientoManual)}
          opciones={Object.entries(MOVIMIENTOS_A_MANO).map(([valor, texto]) => ({
            valor,
            texto,
          }))}
        />
        <Campo
          etiqueta="Importe"
          inputMode="decimal"
          required
          placeholder="0.00"
          ayuda="Siempre en positivo."
          value={importe}
          onChange={(evento) => setImporte(evento.target.value)}
        />
        <Campo
          etiqueta="Motivo del movimiento"
          required
          placeholder="Al cofre, flete del proveedor…"
          value={concepto}
          onChange={(evento) => setConcepto(evento.target.value)}
        />
        <Campo
          etiqueta="Comprobante"
          placeholder="0001-00012345"
          ayuda="Opcional, para los gastos."
          value={comprobante}
          onChange={(evento) => setComprobante(evento.target.value)}
        />
        <div className="flex items-end">
          <Boton type="submit" disabled={registrar.isPending}>
            Registrar
          </Boton>
        </div>
      </form>
    </Seccion>
  )
}

/** El arqueo: se declara lo contado y recién ahí aparece lo esperado. */
function Cierre({
  alCerrar,
  alFallar,
}: {
  alCerrar: () => void
  alFallar: (fallo: unknown) => void
}) {
  const [abierto, setAbierto] = useState(false)
  const [contado, setContado] = useState('')
  const [fondo, setFondo] = useState('')
  const [motivo, setMotivo] = useState('')
  const [observaciones, setObservaciones] = useState('')
  const [arqueo, setArqueo] = useState<SesionCaja | null>(null)

  const sugerido = useQuery({
    queryKey: ['fondo-sugerido'],
    queryFn: () => pedir<{ fondo_sugerido: string }>('/caja/fondo-sugerido'),
  })
  const [fondoTocado, setFondoTocado] = useState(false)
  const valorFondo = fondoTocado ? fondo : (sugerido.data?.fondo_sugerido ?? '')

  const cerrar = useMutation({
    mutationFn: () =>
      pedir<SesionCaja>('/caja/cierre', {
        metodo: 'POST',
        cuerpo: {
          efectivo_declarado: contado,
          fondo_a_dejar: valorFondo,
          motivo_diferencia: motivo === '' ? null : motivo,
          observaciones: observaciones === '' ? null : observaciones,
        },
      }),
    onSuccess: (cerrada) => {
      setArqueo(cerrada)
      alCerrar()
    },
    onError: alFallar,
  })

  if (arqueo !== null) return <ResumenArqueo sesion={arqueo} />

  if (!abierto) {
    return (
      <div>
        <Boton
          onClick={() => {
            setAbierto(true)
          }}
        >
          Cerrar la caja
        </Boton>
      </div>
    )
  }

  return (
    <Seccion titulo="Cerrar la caja">
      <p className="text-sm text-slate-600">
        Contá todo el efectivo del cajón, incluido el fondo con el que se abrió. Escribí
        lo que encontraste: recién después el sistema te dice cuánto esperaba.
      </p>
      <form
        onSubmit={(evento) => {
          evento.preventDefault()
          cerrar.mutate()
        }}
        className="grid gap-4 sm:grid-cols-2"
      >
        <Campo
          etiqueta="Efectivo que contaste"
          inputMode="decimal"
          required
          placeholder="0.00"
          value={contado}
          onChange={(evento) => setContado(evento.target.value)}
        />
        <Campo
          etiqueta="Cuánto dejás para mañana"
          inputMode="decimal"
          required
          placeholder="0.00"
          ayuda="El fondo para dar vuelto. Lo que sobra se retira."
          value={valorFondo}
          onChange={(evento) => {
            setFondoTocado(true)
            setFondo(evento.target.value)
          }}
        />
        <Campo
          etiqueta="Si no coincide, explicá por qué"
          placeholder="Vuelto mal dado, billete faltante…"
          ayuda="Solo hace falta si el arqueo da distinto."
          value={motivo}
          onChange={(evento) => setMotivo(evento.target.value)}
        />
        <Campo
          etiqueta="Observaciones"
          placeholder="Lo que quieras dejar anotado del día"
          value={observaciones}
          onChange={(evento) => setObservaciones(evento.target.value)}
        />
        <div className="flex items-end gap-2 sm:col-span-2">
          <Boton type="submit" disabled={cerrar.isPending || contado === ''}>
            Cerrar y ver el arqueo
          </Boton>
          <Boton
            variante="secundario"
            onClick={() => {
              setAbierto(false)
            }}
          >
            Todavía no
          </Boton>
        </div>
      </form>
    </Seccion>
  )
}

/** Lo que se muestra una vez cerrada la caja. */
export function ResumenArqueo({ sesion }: { sesion: SesionCaja }) {
  const diferencia = sesion.diferencia ?? '0'
  const hayDiferencia = !esCero(diferencia)

  return (
    <Seccion titulo="Arqueo del cierre">
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-sm text-slate-500">Contaste</dt>
          <dd className="text-lg tabular-nums">
            {formatearPesos(sesion.efectivo_declarado)}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-500">El sistema esperaba</dt>
          <dd className="text-lg tabular-nums">
            {formatearPesos(sesion.efectivo_esperado)}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-500">Diferencia</dt>
          <dd
            className={`text-lg tabular-nums ${
              hayDiferencia ? 'font-medium text-amber-700' : 'text-slate-900'
            }`}
          >
            {formatearPesos(diferencia)}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-500">Se retiró</dt>
          <dd className="text-lg tabular-nums">
            {formatearPesos(sesion.monto_retirado)}
          </dd>
        </div>
      </dl>
      {sesion.motivo_diferencia !== null ? (
        <p className="text-sm text-slate-700">
          <span className="text-slate-500">Motivo: </span>
          {sesion.motivo_diferencia}
        </p>
      ) : null}
      <p className="text-sm text-slate-600">
        Quedaron {formatearPesos(sesion.fondo_dejado)} en el cajón para mañana.
      </p>
    </Seccion>
  )
}
