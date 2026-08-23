/** El historial de todo lo que entró y salió. */

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { Ayuda } from '../componentes/Ayuda'
import { Selector } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { pedir } from '../lib/api'
import { useSucursales } from '../lib/catalogos'
import { NOMBRE_MOVIMIENTO, opcionesDe } from '../lib/etiquetas'
import { formatearFechaHora } from '../lib/fecha'
import type { MovimientoStock } from '../lib/tipos'

const COLUMNAS: Columna<MovimientoStock>[] = [
  {
    clave: 'prenda',
    titulo: 'Prenda',
    principal: true,
    valor: (m) => (
      <span>
        {m.producto}
        <span className="text-slate-500">
          {' '}
          · {m.talle} · {m.color}
        </span>
      </span>
    ),
  },
  { clave: 'tipo', titulo: 'Qué pasó', valor: (m) => NOMBRE_MOVIMIENTO[m.tipo] },
  { clave: 'sucursal', titulo: 'Local', valor: (m) => m.sucursal, soloTabla: true },
  {
    clave: 'cantidad',
    titulo: 'Unidades',
    alDerecha: true,
    valor: (m) => (
      <span className={m.cantidad < 0 ? 'text-red-700' : 'text-green-800'}>
        {m.cantidad > 0 ? `+${m.cantidad}` : m.cantidad}
      </span>
    ),
  },
  {
    clave: 'resultante',
    titulo: 'Quedó',
    alDerecha: true,
    valor: (m) => m.cantidad_resultante,
  },
  { clave: 'motivo', titulo: 'Motivo', valor: (m) => m.motivo ?? '—', soloTabla: true },
  {
    clave: 'fecha',
    titulo: 'Cuándo',
    valor: (m) => formatearFechaHora(m.fecha),
    soloTabla: true,
  },
]

export function Movimientos() {
  const sucursales = useSucursales()
  const [sucursalId, setSucursalId] = useState('')
  const [tipo, setTipo] = useState('')

  const movimientos = useQuery({
    queryKey: ['movimientos', sucursalId, tipo],
    queryFn: () => {
      const parametros = new URLSearchParams()
      if (sucursalId !== '') parametros.set('sucursal_id', sucursalId)
      if (tipo !== '') parametros.set('tipo', tipo)
      const cola = parametros.toString()
      return pedir<MovimientoStock[]>(
        `/stock/movimientos${cola === '' ? '' : `?${cola}`}`,
      )
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Movimientos</h1>
        <p className="mt-1 text-sm text-slate-600">
          Todo lo que entró y salió, de lo más nuevo a lo más viejo. No se puede borrar
          nada: una carga equivocada se arregla con una corrección.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Selector
          etiqueta="Local"
          value={sucursalId}
          onChange={(evento) => setSucursalId(evento.target.value)}
          opciones={[
            { valor: '', texto: 'Todos' },
            ...(sucursales.data ?? []).map((s) => ({ valor: s.id, texto: s.nombre })),
          ]}
        />
        <Selector
          etiqueta="Qué pasó"
          value={tipo}
          onChange={(evento) => setTipo(evento.target.value)}
          opciones={[{ valor: '', texto: 'Todo' }, ...opcionesDe(NOMBRE_MOVIMIENTO)]}
        />
      </div>

      <Listado
        columnas={COLUMNAS}
        filas={movimientos.data ?? []}
        claveDe={(m) => m.id}
        cargando={movimientos.isPending}
        vacio="Todavía no se movió nada."
      />

      <Ayuda pantalla="movimientos" />
    </div>
  )
}
