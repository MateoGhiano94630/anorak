/** Deja pasar solo a quien entró, y solo a los puestos que corresponden. */

import { Navigate, Outlet } from 'react-router-dom'

import { useSesion } from '../contexto/sesion'
import type { Rol } from '../lib/tipos'

export function RutaProtegida({ roles }: { roles?: Rol[] }) {
  const { usuario } = useSesion()

  if (usuario === null) return <Navigate to="/ingreso" replace />

  // El administrador entra a todo: no hace falta nombrarlo en cada ruta, que
  // es la forma segura de olvidárselo en alguna.
  const permitido =
    roles === undefined || usuario.rol === 'ADMIN' || roles.includes(usuario.rol)

  if (!permitido) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h1 className="text-lg font-semibold">Esta sección no es de tu puesto</h1>
        <p className="mt-2 text-sm text-slate-700">
          Tu cuenta no tiene acceso a esta parte del sistema. Si necesitás entrar,
          pedíselo al administrador.
        </p>
      </div>
    )
  }

  return <Outlet />
}
