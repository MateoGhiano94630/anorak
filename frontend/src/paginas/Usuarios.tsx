/** Alta y mantenimiento de las cuentas del sistema. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo, Selector } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { useSesion } from '../contexto/sesion'
import { ErrorApi, pedir } from '../lib/api'
import { NOMBRE_ROL, opcionesDe } from '../lib/etiquetas'
import { formatearFechaHora } from '../lib/fecha'
import type { Rol, Usuario } from '../lib/tipos'

export function Usuarios() {
  const clienteConsultas = useQueryClient()
  const { usuario: propio } = useSesion()
  const [nombre, setNombre] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rol, setRol] = useState<Rol>('VENDEDOR')
  const [error, setError] = useState<string | null>(null)

  const usuarios = useQuery({
    queryKey: ['usuarios'],
    queryFn: () => pedir<Usuario[]>('/usuarios'),
  })
  function refrescar(): void {
    void clienteConsultas.invalidateQueries({ queryKey: ['usuarios'] })
  }

  const alta = useMutation({
    mutationFn: () =>
      pedir<Usuario>('/usuarios', {
        metodo: 'POST',
        cuerpo: { nombre, email, password, rol },
      }),
    onSuccess: () => {
      setNombre('')
      setEmail('')
      setPassword('')
      setError(null)
      refrescar()
    },
    onError: (fallo) =>
      setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo guardar.'),
  })

  const cambioEstado = useMutation({
    mutationFn: (fila: Usuario) =>
      pedir<Usuario>(`/usuarios/${fila.id}`, {
        metodo: 'PATCH',
        cuerpo: { activo: !fila.activo },
      }),
    onSuccess: () => {
      setError(null)
      refrescar()
    },
    onError: (fallo) =>
      setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo guardar.'),
  })

  const columnas: Columna<Usuario>[] = [
    { clave: 'nombre', titulo: 'Nombre', valor: (u) => u.nombre, principal: true },
    { clave: 'email', titulo: 'Correo', valor: (u) => u.email },
    { clave: 'rol', titulo: 'Puesto', valor: (u) => NOMBRE_ROL[u.rol] },
    {
      clave: 'ultimo',
      titulo: 'Último ingreso',
      valor: (u) => formatearFechaHora(u.ultimo_ingreso) || 'Nunca entró',
      soloTabla: true,
    },
    {
      clave: 'estado',
      titulo: 'Estado',
      valor: (u) => (
        <Boton
          variante={u.activo ? 'secundario' : 'principal'}
          disabled={u.id === propio?.id || cambioEstado.isPending}
          onClick={() => cambioEstado.mutate(u)}
        >
          {u.activo ? 'Dar de baja' : 'Activar'}
        </Boton>
      ),
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Usuarios</h1>

      <form
        onSubmit={(evento) => {
          evento.preventDefault()
          alta.mutate()
        }}
        className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        <Campo
          etiqueta="Nombre"
          required
          value={nombre}
          onChange={(evento) => setNombre(evento.target.value)}
        />
        <Campo
          etiqueta="Correo"
          type="email"
          required
          value={email}
          onChange={(evento) => setEmail(evento.target.value)}
        />
        <Campo
          etiqueta="Contraseña"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          ayuda="Mínimo 8 caracteres. La persona la cambia al entrar."
          value={password}
          onChange={(evento) => setPassword(evento.target.value)}
        />
        <Selector
          etiqueta="Puesto"
          value={rol}
          onChange={(evento) => setRol(evento.target.value as Rol)}
          opciones={opcionesDe(NOMBRE_ROL)}
        />
        <div className="flex items-end">
          <Boton type="submit" disabled={alta.isPending}>
            Agregar
          </Boton>
        </div>
      </form>

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <Listado
        columnas={columnas}
        filas={usuarios.data ?? []}
        claveDe={(usuario) => usuario.id}
        cargando={usuarios.isPending}
        vacio="Todavía no hay ninguna cuenta cargada."
      />

      <Ayuda pantalla="usuarios" />
    </div>
  )
}
