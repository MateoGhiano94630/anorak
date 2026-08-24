/** El historial de cierres, que es donde se ven las diferencias juntas. */

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Ayuda } from '../componentes/Ayuda'
import { Listado, type Columna } from '../componentes/Listado'
import { pedir } from '../lib/api'
import { formatearPesos } from '../lib/dinero'
import { esCero } from '../lib/importes'
import { formatearFechaHora } from '../lib/fecha'
import type { SesionCaja, SesionEnLista } from '../lib/tipos'
import { ResumenArqueo } from './Caja'

/** Una diferencia distinta de cero se marca; el cero se muestra tranquilo. */
function Diferencia({ valor }: { valor: string | null }) {
  if (valor === null) return <span className="text-slate-500">Sin cerrar</span>
  const hay = !esCero(valor)
  return (
    <span className={hay ? 'font-medium text-amber-700' : ''}>
      {formatearPesos(valor)}
    </span>
  )
}

const COLUMNAS: Columna<SesionEnLista>[] = [
  {
    clave: 'fecha',
    titulo: 'Día',
    principal: true,
    valor: (s) => formatearFechaHora(s.fecha_apertura),
  },
  { clave: 'abrio', titulo: 'La abrió', valor: (s) => s.abierta_por_nombre ?? '—' },
  {
    clave: 'cerro',
    titulo: 'La cerró',
    valor: (s) => s.cerrada_por_nombre ?? '—',
    soloTabla: true,
  },
  {
    clave: 'contado',
    titulo: 'Contado',
    alDerecha: true,
    valor: (s) => formatearPesos(s.efectivo_declarado),
    soloTabla: true,
  },
  {
    clave: 'esperado',
    titulo: 'Esperado',
    alDerecha: true,
    valor: (s) => formatearPesos(s.efectivo_esperado),
    soloTabla: true,
  },
  {
    clave: 'diferencia',
    titulo: 'Diferencia',
    alDerecha: true,
    valor: (s) => <Diferencia valor={s.diferencia} />,
  },
  {
    clave: 'retirado',
    titulo: 'Se retiró',
    alDerecha: true,
    valor: (s) => formatearPesos(s.monto_retirado),
    soloTabla: true,
  },
]

export function CierresCaja() {
  const [abierta, setAbierta] = useState<string | null>(null)

  const sesiones = useQuery({
    queryKey: ['sesiones-caja'],
    queryFn: () => pedir<SesionEnLista[]>('/caja/sesiones'),
  })

  const detalle = useQuery({
    queryKey: ['sesion-caja', abierta],
    queryFn: () => pedir<SesionCaja>(`/caja/sesiones/${abierta ?? ''}`),
    enabled: abierta !== null,
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to="/caja" className="text-sm text-slate-600 underline">
          Volver a la caja
        </Link>
        <h1 className="mt-2 text-xl font-semibold">Cierres de caja</h1>
        <p className="mt-1 text-sm text-slate-600">
          Lo que importa no es un faltante suelto, sino si se repite. Por eso están todos
          juntos.
        </p>
      </div>

      <Listado
        columnas={COLUMNAS}
        filas={sesiones.data ?? []}
        claveDe={(s) => s.id}
        cargando={sesiones.isPending}
        vacio="Todavía no se cerró ninguna caja."
        alTocarFila={(s) => {
          setAbierta((estaba) => (estaba === s.id ? null : s.id))
        }}
      />

      {abierta !== null && detalle.data !== undefined ? (
        <ResumenArqueo sesion={detalle.data} />
      ) : null}

      <Ayuda pantalla="historialCaja" />
    </div>
  )
}
