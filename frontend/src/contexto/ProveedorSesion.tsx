/** Mantiene la sesión abierta mientras dure la pestaña. */

import { useCallback, useEffect, useMemo, useState } from 'react'

import { EVENTO_SESION_VENCIDA, pedir } from '../lib/api'
import { guardarToken, limpiarToken } from '../lib/sesion'
import type { RespuestaIngreso, UsuarioActual } from '../lib/tipos'
import { ContextoSesion, type Sesion } from './sesion'

export function ProveedorSesion({ children }: { children: React.ReactNode }) {
  const [usuario, setUsuario] = useState<UsuarioActual | null>(null)
  const [ingresando, setIngresando] = useState(false)

  const salir = useCallback(() => {
    limpiarToken()
    setUsuario(null)
  }, [])

  // Si el servidor rechaza el token a mitad de una jornada (venció, o la
  // cuenta se dio de baja), la pantalla tiene que volver al ingreso sola. Sin
  // esto, quedaría mostrando datos viejos y cada acción fallaría en silencio.
  useEffect(() => {
    window.addEventListener(EVENTO_SESION_VENCIDA, salir)
    return () => window.removeEventListener(EVENTO_SESION_VENCIDA, salir)
  }, [salir])

  const ingresar = useCallback(async (email: string, password: string) => {
    setIngresando(true)
    try {
      const respuesta = await pedir<RespuestaIngreso>('/auth/login', {
        metodo: 'POST',
        cuerpo: { email, password },
        sinSesion: true,
      })
      guardarToken(respuesta.access_token)
      setUsuario(respuesta.usuario)
    } finally {
      setIngresando(false)
    }
  }, [])

  const valor = useMemo<Sesion>(
    () => ({ usuario, ingresando, ingresar, salir }),
    [usuario, ingresando, ingresar, salir],
  )

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>
}
