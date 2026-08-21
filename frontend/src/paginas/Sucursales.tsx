/** Alta y consulta de sucursales. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo, Selector } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { ErrorApi, pedir } from '../lib/api'
import type { Sucursal, TipoSucursal } from '../lib/tipos'

const COLUMNAS: Columna<Sucursal>[] = [
  { clave: 'nombre', titulo: 'Nombre', valor: (s) => s.nombre, principal: true },
  { clave: 'codigo', titulo: 'Código', valor: (s) => s.codigo },
  {
    clave: 'tipo',
    titulo: 'Tipo',
    valor: (s) => (s.tipo === 'LOCAL' ? 'Local' : 'Depósito'),
  },
  {
    clave: 'direccion',
    titulo: 'Dirección',
    valor: (s) => s.direccion ?? '—',
    soloTabla: true,
  },
  {
    clave: 'estado',
    titulo: 'Estado',
    valor: (s) => (s.activa ? 'Activa' : 'Dada de baja'),
  },
]

export function Sucursales() {
  const clienteConsultas = useQueryClient()
  const [nombre, setNombre] = useState('')
  const [codigo, setCodigo] = useState('')
  const [tipo, setTipo] = useState<TipoSucursal>('LOCAL')
  const [error, setError] = useState<string | null>(null)

  const consulta = useQuery({
    queryKey: ['sucursales'],
    queryFn: () => pedir<Sucursal[]>('/sucursales'),
  })

  const alta = useMutation({
    mutationFn: () =>
      pedir<Sucursal>('/sucursales', {
        metodo: 'POST',
        cuerpo: { nombre, codigo, tipo },
      }),
    onSuccess: () => {
      setNombre('')
      setCodigo('')
      setError(null)
      void clienteConsultas.invalidateQueries({ queryKey: ['sucursales'] })
    },
    onError: (fallo) => {
      setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo guardar.')
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Sucursales</h1>

      <form
        onSubmit={(evento) => {
          evento.preventDefault()
          alta.mutate()
        }}
        className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:flex-row sm:items-end"
      >
        <div className="flex-1">
          <Campo
            etiqueta="Nombre"
            required
            value={nombre}
            onChange={(evento) => setNombre(evento.target.value)}
          />
        </div>
        <div className="sm:w-32">
          <Campo
            etiqueta="Código"
            required
            maxLength={10}
            ayuda="Corto, para listados."
            value={codigo}
            onChange={(evento) => setCodigo(evento.target.value.toUpperCase())}
          />
        </div>
        <div className="sm:w-40">
          <Selector
            etiqueta="Tipo"
            value={tipo}
            onChange={(evento) => setTipo(evento.target.value as TipoSucursal)}
            opciones={[
              { valor: 'LOCAL', texto: 'Local' },
              { valor: 'DEPOSITO', texto: 'Depósito' },
            ]}
          />
        </div>
        <Boton type="submit" disabled={alta.isPending}>
          Agregar
        </Boton>
      </form>

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <Listado
        columnas={COLUMNAS}
        filas={consulta.data ?? []}
        claveDe={(sucursal) => sucursal.id}
        cargando={consulta.isPending}
        vacio="Todavía no hay ninguna sucursal cargada."
      />

      <Ayuda pantalla="sucursales" />
    </div>
  )
}
