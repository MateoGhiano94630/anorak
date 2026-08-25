/** Las ventas del local, con el detalle de cada una y su anulación. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { ErrorApi, pedir } from '../lib/api'
import { formatearPesos } from '../lib/dinero'
import { NOMBRE_ESTADO_VENTA } from '../lib/etiquetas'
import { formatearFechaHora } from '../lib/fecha'
import type { Venta, VentaEnLista } from '../lib/tipos'

const COLUMNAS: Columna<VentaEnLista>[] = [
  {
    clave: 'numero',
    titulo: 'Venta',
    principal: true,
    valor: (v) => (
      <span>
        #{v.numero}
        {v.estado === 'ANULADA' ? (
          <span className="ml-2 text-amber-700">Anulada</span>
        ) : null}
      </span>
    ),
  },
  { clave: 'fecha', titulo: 'Cuándo', valor: (v) => formatearFechaHora(v.fecha) },
  {
    clave: 'quien',
    titulo: 'La hizo',
    valor: (v) => v.registrada_por_nombre ?? '—',
    soloTabla: true,
  },
  {
    clave: 'articulos',
    titulo: 'Prendas',
    alDerecha: true,
    valor: (v) => v.cantidad_articulos,
  },
  {
    clave: 'total',
    titulo: 'Total',
    alDerecha: true,
    valor: (v) => (
      <span className={v.estado === 'ANULADA' ? 'text-slate-400 line-through' : ''}>
        {formatearPesos(v.total)}
      </span>
    ),
  },
]

export function Ventas() {
  const clienteConsultas = useQueryClient()
  const [buscar, setBuscar] = useState('')
  const [abierta, setAbierta] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const ventas = useQuery({
    queryKey: ['ventas', buscar],
    queryFn: () => {
      const cola =
        buscar.trim() === '' ? '' : `?buscar=${encodeURIComponent(buscar.trim())}`
      return pedir<VentaEnLista[]>(`/ventas${cola}`)
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Ventas</h1>

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <Campo
        etiqueta="Buscar"
        type="search"
        placeholder="#12, o campera"
        ayuda="Por número de venta o por lo que dice alguna de sus líneas."
        value={buscar}
        onChange={(evento) => setBuscar(evento.target.value)}
      />

      <Listado
        columnas={COLUMNAS}
        filas={ventas.data ?? []}
        claveDe={(v) => v.id}
        cargando={ventas.isPending}
        vacio={
          buscar.trim() === ''
            ? 'Todavía no se registró ninguna venta.'
            : 'Ninguna venta coincide con lo que buscaste.'
        }
        alTocarFila={(v) => {
          setAbierta((estaba) => (estaba === v.id ? null : v.id))
          setError(null)
        }}
      />

      {abierta !== null ? (
        <DetalleVenta
          key={abierta}
          ventaId={abierta}
          alCambiar={() => {
            setError(null)
            void clienteConsultas.invalidateQueries({ queryKey: ['ventas'] })
            void clienteConsultas.invalidateQueries({ queryKey: ['caja'] })
          }}
          alFallar={(fallo) => {
            setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo anular.')
          }}
        />
      ) : null}

      <Ayuda pantalla="ventas" />
    </div>
  )
}

interface DetalleProps {
  ventaId: string
  alCambiar: () => void
  alFallar: (fallo: unknown) => void
}

/** El detalle de una venta: qué se vendió, cómo se pagó, y su anulación. */
function DetalleVenta({ ventaId, alCambiar, alFallar }: DetalleProps) {
  const clienteConsultas = useQueryClient()
  const [motivo, setMotivo] = useState('')

  const venta = useQuery({
    queryKey: ['venta', ventaId],
    queryFn: () => pedir<Venta>(`/ventas/${ventaId}`),
  })

  const anular = useMutation({
    mutationFn: () =>
      pedir<Venta>(`/ventas/${ventaId}/anulacion`, {
        metodo: 'POST',
        cuerpo: { motivo },
      }),
    onSuccess: () => {
      setMotivo('')
      void clienteConsultas.invalidateQueries({ queryKey: ['venta', ventaId] })
      alCambiar()
    },
    onError: alFallar,
  })

  if (venta.isPending) return <p className="text-slate-500">Cargando…</p>
  if (venta.data === undefined) return null

  const datos = venta.data
  const anulada = datos.estado === 'ANULADA'

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-medium">
          Venta #{datos.numero} · {NOMBRE_ESTADO_VENTA[datos.estado]}
        </h2>
        <span className="text-sm text-slate-600">
          {formatearFechaHora(datos.fecha)} · {datos.registrada_por_nombre ?? '—'}
        </span>
      </div>

      <ul className="flex flex-col gap-1 text-sm">
        {datos.lineas.map((linea) => (
          <li key={linea.id} className="flex justify-between gap-4">
            <span>
              {linea.cantidad} × {linea.descripcion}
              {linea.talle !== null ? (
                <span className="text-slate-500"> · talle {linea.talle}</span>
              ) : null}
            </span>
            <span className="tabular-nums">{formatearPesos(linea.subtotal)}</span>
          </li>
        ))}
      </ul>

      <dl className="flex flex-col gap-1 border-t border-slate-200 pt-3 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-slate-600">Suma de las líneas</dt>
          <dd className="tabular-nums">{formatearPesos(datos.subtotal)}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-600">Descuento</dt>
          <dd className="tabular-nums">{formatearPesos(datos.descuento)}</dd>
        </div>
        <div className="flex justify-between gap-4 text-base font-medium">
          <dt>Total</dt>
          <dd className="tabular-nums">{formatearPesos(datos.total)}</dd>
        </div>
      </dl>

      <div>
        <p className="text-sm font-medium text-slate-700">Cómo se pagó</p>
        <ul className="mt-1 flex flex-col gap-1 text-sm">
          {datos.cobros.map((cobro, indice) => (
            <li
              key={`${cobro.medio_pago_id}-${indice}`}
              className="flex justify-between gap-4"
            >
              <span className="text-slate-600">
                {cobro.medio_pago}
                {cobro.es_reversion ? ' (devuelto al anular)' : ''}
              </span>
              <span className="tabular-nums">{formatearPesos(cobro.importe)}</span>
            </li>
          ))}
        </ul>
      </div>

      {anulada ? (
        <p className="text-sm text-amber-800">
          Anulada por {datos.anulada_por_nombre ?? '—'} el{' '}
          {formatearFechaHora(datos.fecha_anulacion)}: {datos.motivo_anulacion}
        </p>
      ) : (
        <div className="flex flex-col gap-3 border-t border-slate-200 pt-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Campo
              etiqueta="Motivo de la anulación"
              placeholder="Se cargó mal, el cliente se arrepintió…"
              ayuda="La venta no se borra: queda anulada y la plata vuelve a la caja."
              value={motivo}
              onChange={(evento) => setMotivo(evento.target.value)}
            />
          </div>
          <Boton
            variante="peligro"
            disabled={motivo.trim() === '' || anular.isPending}
            onClick={() => {
              anular.mutate()
            }}
          >
            Anular la venta
          </Boton>
        </div>
      )}
    </section>
  )
}
