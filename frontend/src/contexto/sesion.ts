/** El contexto de la sesión y el gancho para leerlo desde cualquier pantalla. */

import { createContext, useContext } from 'react'

import type { UsuarioActual } from '../lib/tipos'

export interface Sesion {
  /** Quién está usando el sistema, o null si no entró nadie. */
  usuario: UsuarioActual | null
  /** True mientras se está verificando el ingreso. */
  ingresando: boolean
  ingresar: (email: string, password: string) => Promise<void>
  salir: () => void
}

export const ContextoSesion = createContext<Sesion | null>(null)

/** Devuelve la sesión actual. Falla si se usa fuera del proveedor. */
export function useSesion(): Sesion {
  const sesion = useContext(ContextoSesion)
  if (sesion === null) {
    throw new Error('useSesion se usó fuera de <ProveedorSesion>')
  }
  return sesion
}
