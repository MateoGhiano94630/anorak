/** Pantalla de ingreso al sistema. */

import { useState } from 'react'
import { Navigate } from 'react-router-dom'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo } from '../componentes/Campo'
import { useSesion } from '../contexto/sesion'
import { ErrorApi } from '../lib/api'

export function Ingreso() {
  const { usuario, ingresar, ingresando } = useSesion()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  if (usuario !== null) return <Navigate to="/" replace />

  async function manejarEnvio(evento: React.SyntheticEvent): Promise<void> {
    evento.preventDefault()
    setError(null)
    try {
      await ingresar(email.trim().toLowerCase(), password)
    } catch (fallo) {
      setError(
        fallo instanceof ErrorApi ? fallo.message : 'No se pudo entrar. Probá de nuevo.',
      )
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold text-slate-900">Anorak</h1>
        <p className="mt-1 text-sm text-slate-600">Gestión del local</p>

        <form
          onSubmit={(evento) => void manejarEnvio(evento)}
          className="mt-6 flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-6"
        >
          <Campo
            etiqueta="Correo"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(evento) => setEmail(evento.target.value)}
          />
          <Campo
            etiqueta="Contraseña"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(evento) => setPassword(evento.target.value)}
          />
          {error !== null ? (
            <p role="alert" className="text-sm text-red-700">
              {error}
            </p>
          ) : null}
          <Boton type="submit" disabled={ingresando}>
            {ingresando ? 'Entrando…' : 'Entrar'}
          </Boton>
        </form>

        <div className="mt-4">
          <Ayuda pantalla="ingreso" />
        </div>
      </div>
    </div>
  )
}
