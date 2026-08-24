/** Pantalla de inicio: desde acá se llega al resto del sistema. */

import { Link } from 'react-router-dom'

import { Ayuda } from '../componentes/Ayuda'
import { useSesion } from '../contexto/sesion'
import type { Rol } from '../lib/tipos'

interface Acceso {
  ruta: string
  titulo: string
  detalle: string
  roles: Rol[]
}

const ACCESOS: Acceso[] = [
  {
    ruta: '/usuarios',
    titulo: 'Usuarios',
    detalle: 'Quién entra al sistema y qué puede hacer.',
    roles: ['ADMIN'],
  },
]

export function Inicio() {
  const { usuario } = useSesion()
  if (usuario === null) return null

  const disponibles = ACCESOS.filter(
    (acceso) => usuario.rol === 'ADMIN' || acceso.roles.includes(usuario.rol),
  )

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Hola, {usuario.nombre}</h1>
        <p className="mt-1 text-sm text-slate-600">
          Los módulos del negocio se suman en las próximas etapas.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {disponibles.map((acceso) => (
          <Link
            key={acceso.ruta}
            to={acceso.ruta}
            className="rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400"
          >
            <p className="font-medium text-slate-900">{acceso.titulo}</p>
            <p className="mt-1 text-sm text-slate-600">{acceso.detalle}</p>
          </Link>
        ))}
      </div>

      <Ayuda pantalla="inicio" />
    </div>
  )
}
