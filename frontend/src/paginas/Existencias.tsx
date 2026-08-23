/** Existencias: cuánto hay de cada prenda en cada local. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo, Selector } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { useSesion } from '../contexto/sesion'
import { ErrorApi, pedir } from '../lib/api'
import { useSucursales } from '../lib/catalogos'
import type { ExistenciaStock } from '../lib/tipos'

export function Existencias() {
  const clienteConsultas = useQueryClient()
  const { usuario } = useSesion()
  const puedeCorregir = usuario?.rol === 'ADMIN' || usuario?.rol === 'ENCARGADO'
  const sucursales = useSucursales()

  const [buscar, setBuscar] = useState('')
  const [sucursalId, setSucursalId] = useState('')
  const [soloBajoMinimo, setSoloBajoMinimo] = useState(false)
  const [abierta, setAbierta] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const existencias = useQuery({
    queryKey: ['stock', buscar, sucursalId, soloBajoMinimo],
    queryFn: () => {
      const parametros = new URLSearchParams()
      if (buscar.trim() !== '') parametros.set('buscar', buscar.trim())
      if (sucursalId !== '') parametros.set('sucursal_id', sucursalId)
      if (soloBajoMinimo) parametros.set('solo_bajo_minimo', 'true')
      const cola = parametros.toString()
      return pedir<ExistenciaStock[]>(`/stock${cola === '' ? '' : `?${cola}`}`)
    },
  })

  const columnas: Columna<ExistenciaStock>[] = [
    {
      clave: 'prenda',
      titulo: 'Prenda',
      principal: true,
      valor: (fila) => (
        <span>
          {fila.producto}
          <span className="text-slate-500">
            {' '}
            · {fila.talle} · {fila.color}
          </span>
        </span>
      ),
    },
    { clave: 'sku', titulo: 'Código', valor: (fila) => fila.sku, soloTabla: true },
    { clave: 'sucursal', titulo: 'Local', valor: (fila) => fila.sucursal },
    {
      clave: 'cantidad',
      titulo: 'Hay',
      alDerecha: true,
      valor: (fila) => (
        <span className={fila.bajo_minimo ? 'font-medium text-amber-700' : ''}>
          {fila.cantidad}
          {fila.bajo_minimo ? ' ⚠' : ''}
        </span>
      ),
    },
    {
      clave: 'minimo',
      titulo: 'Reponer en',
      alDerecha: true,
      valor: (fila) => (fila.stock_minimo === 0 ? '—' : fila.stock_minimo),
      soloTabla: true,
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Existencias</h1>

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <Campo
          etiqueta="Buscar"
          type="search"
          placeholder="Prenda o código"
          value={buscar}
          onChange={(evento) => setBuscar(evento.target.value)}
        />
        <Selector
          etiqueta="Local"
          value={sucursalId}
          onChange={(evento) => setSucursalId(evento.target.value)}
          opciones={[
            { valor: '', texto: 'Todos' },
            ...(sucursales.data ?? []).map((s) => ({ valor: s.id, texto: s.nombre })),
          ]}
        />
        <label className="flex items-end gap-2 pb-2 text-base text-slate-700">
          <input
            type="checkbox"
            className="size-5"
            checked={soloBajoMinimo}
            onChange={(evento) => setSoloBajoMinimo(evento.target.checked)}
          />
          Solo lo que hay que reponer
        </label>
      </div>

      <Listado
        columnas={columnas}
        filas={existencias.data ?? []}
        claveDe={(fila) => `${fila.variante_id}-${fila.sucursal_id}`}
        cargando={existencias.isPending}
        vacio={
          soloBajoMinimo
            ? 'No hay nada por debajo de su mínimo. '
            : 'Todavía no hay mercadería cargada en ningún local.'
        }
        alTocarFila={
          puedeCorregir
            ? (fila) => {
                const clave = `${fila.variante_id}-${fila.sucursal_id}`
                setAbierta((estaba) => (estaba === clave ? null : clave))
              }
            : undefined
        }
      />

      {abierta !== null ? (
        <PanelExistencia
          key={abierta}
          fila={(existencias.data ?? []).find(
            (f) => `${f.variante_id}-${f.sucursal_id}` === abierta,
          )}
          alGuardar={() => {
            setError(null)
            void clienteConsultas.invalidateQueries({ queryKey: ['stock'] })
          }}
          alFallar={(fallo) => {
            setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo guardar.')
          }}
        />
      ) : null}

      {puedeCorregir ? <CargaDeMercaderia /> : null}

      <p className="text-sm text-slate-600">
        Para ver todo lo que entró y salió, entrá a{' '}
        <Link to="/movimientos" className="underline">
          Movimientos
        </Link>
        .
      </p>

      <Ayuda pantalla="existencias" />
    </div>
  )
}

interface PanelProps {
  fila: ExistenciaStock | undefined
  alGuardar: () => void
  alFallar: (fallo: unknown) => void
}

/** El panel que se abre al tocar una prenda: cargar, ajustar y fijar el mínimo. */
function PanelExistencia({ fila, alGuardar, alFallar }: PanelProps) {
  const [cantidad, setCantidad] = useState('')
  const [contado, setContado] = useState('')
  const [motivo, setMotivo] = useState('')
  const [minimo, setMinimo] = useState(String(fila?.stock_minimo ?? 0))

  const cuerpoBase = {
    variante_id: fila?.variante_id ?? '',
    sucursal_id: fila?.sucursal_id ?? '',
  }

  const cargar = useMutation({
    mutationFn: () =>
      pedir<ExistenciaStock>('/stock/ingresos', {
        metodo: 'POST',
        cuerpo: { ...cuerpoBase, cantidad: Number(cantidad), motivo },
      }),
    onSuccess: () => {
      setCantidad('')
      setMotivo('')
      alGuardar()
    },
    onError: alFallar,
  })

  const ajustar = useMutation({
    mutationFn: () =>
      pedir<ExistenciaStock>('/stock/ajustes', {
        metodo: 'POST',
        cuerpo: { ...cuerpoBase, cantidad_final: Number(contado), motivo },
      }),
    onSuccess: () => {
      setContado('')
      setMotivo('')
      alGuardar()
    },
    onError: alFallar,
  })

  const guardarMinimo = useMutation({
    mutationFn: () =>
      pedir<ExistenciaStock>('/stock/minimo', {
        metodo: 'POST',
        cuerpo: { ...cuerpoBase, stock_minimo: Number(minimo) },
      }),
    onSuccess: alGuardar,
    onError: alFallar,
  })

  if (fila === undefined) return null

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-sm font-medium">
        {fila.producto} · {fila.talle} · {fila.color} — en {fila.sucursal} hay{' '}
        {fila.cantidad}
      </p>

      {/* La etiqueta dice "del movimiento" y no solo "Motivo" porque más
          abajo, en la carga de mercadería, hay otro campo de motivo. Dos
          campos con el mismo rótulo en una pantalla obligan a adivinar cuál
          es cuál, y un lector de pantalla los lee idénticos. */}
      <Campo
        etiqueta="Motivo del movimiento"
        placeholder="Pedido de temporada, conteo del lunes…"
        ayuda="Queda escrito en el historial. Es lo que después explica el número."
        value={motivo}
        onChange={(evento) => setMotivo(evento.target.value)}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Campo
              etiqueta="Llegó mercadería"
              inputMode="numeric"
              placeholder="0"
              ayuda="Unidades que entraron."
              value={cantidad}
              onChange={(evento) => setCantidad(evento.target.value)}
            />
          </div>
          <Boton
            variante="secundario"
            disabled={cantidad === '' || motivo === '' || cargar.isPending}
            onClick={() => {
              cargar.mutate()
            }}
          >
            Sumar
          </Boton>
        </div>

        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Campo
              etiqueta="Conté y hay"
              inputMode="numeric"
              placeholder="0"
              ayuda="La cantidad real. Se guarda la diferencia."
              value={contado}
              onChange={(evento) => setContado(evento.target.value)}
            />
          </div>
          <Boton
            variante="secundario"
            disabled={contado === '' || motivo === '' || ajustar.isPending}
            onClick={() => {
              ajustar.mutate()
            }}
          >
            Corregir
          </Boton>
        </div>

        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Campo
              etiqueta="Reponer cuando llegue a"
              inputMode="numeric"
              ayuda="Cero es no controlar esta prenda."
              value={minimo}
              onChange={(evento) => setMinimo(evento.target.value)}
            />
          </div>
          <Boton
            variante="secundario"
            disabled={guardarMinimo.isPending}
            onClick={() => {
              guardarMinimo.mutate()
            }}
          >
            Guardar
          </Boton>
        </div>
      </div>
    </div>
  )
}

/** Buscador de una prenda del catálogo para cargarle la primera mercadería. */
function CargaDeMercaderia() {
  const clienteConsultas = useQueryClient()
  const sucursales = useSucursales()
  const [codigo, setCodigo] = useState('')
  const [sucursalId, setSucursalId] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [motivo, setMotivo] = useState('')
  const [aviso, setAviso] = useState<string | null>(null)

  const cargar = useMutation({
    mutationFn: async () => {
      // Se busca por código porque es lo que hay a mano cuando llega el pedido:
      // la etiqueta de la prenda. Pedir que la elijan de una lista de mil
      // combinaciones sería impracticable con la caja llena de bolsas.
      const variante = await pedir<{ id: string }>(
        `/variantes/buscar?codigo=${encodeURIComponent(codigo.trim())}`,
      )
      return pedir<ExistenciaStock>('/stock/ingresos', {
        metodo: 'POST',
        cuerpo: {
          variante_id: variante.id,
          sucursal_id: sucursalId,
          cantidad: Number(cantidad),
          motivo,
        },
      })
    },
    onSuccess: (fila) => {
      setAviso(
        `Quedaron ${fila.cantidad} de ${fila.producto} ${fila.talle} ${fila.color}.`,
      )
      setCodigo('')
      setCantidad('')
      void clienteConsultas.invalidateQueries({ queryKey: ['stock'] })
    },
    onError: (fallo) => {
      setAviso(fallo instanceof ErrorApi ? fallo.message : 'No se pudo cargar.')
    },
  })

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-medium">Cargar mercadería que llegó</h2>
      <form
        onSubmit={(evento) => {
          evento.preventDefault()
          cargar.mutate()
        }}
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5"
      >
        <Campo
          etiqueta="Código de la prenda"
          required
          placeholder="NIKREMLIS-M-NEG"
          ayuda="El interno o el de barras."
          value={codigo}
          onChange={(evento) => setCodigo(evento.target.value)}
        />
        <Selector
          etiqueta="Local que la recibe"
          required
          value={sucursalId}
          onChange={(evento) => setSucursalId(evento.target.value)}
          opciones={[
            { valor: '', texto: 'Elegí uno' },
            ...(sucursales.data ?? []).map((s) => ({ valor: s.id, texto: s.nombre })),
          ]}
        />
        <Campo
          etiqueta="Cantidad"
          inputMode="numeric"
          required
          placeholder="0"
          value={cantidad}
          onChange={(evento) => setCantidad(evento.target.value)}
        />
        <Campo
          etiqueta="Motivo del ingreso"
          required
          placeholder="Pedido de temporada"
          value={motivo}
          onChange={(evento) => setMotivo(evento.target.value)}
        />
        <div className="flex items-end">
          <Boton type="submit" disabled={cargar.isPending}>
            Cargar
          </Boton>
        </div>
      </form>
      {aviso !== null ? <p className="text-sm text-slate-700">{aviso}</p> : null}
    </section>
  )
}
