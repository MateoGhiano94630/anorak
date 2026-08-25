/** El catálogo: lo que el local vende, con su precio. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { ErrorApi, pedir } from '../lib/api'
import { formatearPesos } from '../lib/dinero'
import type { Articulo } from '../lib/tipos'

export function Articulos() {
  const clienteConsultas = useQueryClient()
  const [nombre, setNombre] = useState('')
  const [categoria, setCategoria] = useState('')
  const [precio, setPrecio] = useState('')
  const [buscar, setBuscar] = useState('')
  const [error, setError] = useState<string | null>(null)

  const articulos = useQuery({
    queryKey: ['articulos', buscar, 'todos'],
    queryFn: () => {
      const parametros = new URLSearchParams({ solo_activos: 'false' })
      if (buscar.trim() !== '') parametros.set('buscar', buscar.trim())
      return pedir<Articulo[]>(`/articulos?${parametros.toString()}`)
    },
  })

  function refrescar(): void {
    setError(null)
    void clienteConsultas.invalidateQueries({ queryKey: ['articulos'] })
  }

  function avisar(fallo: unknown): void {
    setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo guardar.')
  }

  const alta = useMutation({
    mutationFn: () =>
      pedir<Articulo>('/articulos', {
        metodo: 'POST',
        cuerpo: {
          nombre,
          categoria: categoria === '' ? null : categoria,
          precio,
        },
      }),
    onSuccess: () => {
      setNombre('')
      setPrecio('')
      refrescar()
    },
    onError: avisar,
  })

  const cambioEstado = useMutation({
    mutationFn: (articulo: Articulo) =>
      pedir<Articulo>(`/articulos/${articulo.id}`, {
        metodo: 'PATCH',
        cuerpo: { activo: !articulo.activo },
      }),
    onSuccess: refrescar,
    onError: avisar,
  })

  const columnas: Columna<Articulo>[] = [
    { clave: 'nombre', titulo: 'Artículo', valor: (a) => a.nombre, principal: true },
    { clave: 'categoria', titulo: 'Categoría', valor: (a) => a.categoria ?? '—' },
    {
      clave: 'precio',
      titulo: 'Precio',
      alDerecha: true,
      valor: (a) => formatearPesos(a.precio),
    },
    {
      clave: 'estado',
      titulo: 'Estado',
      valor: (a) => (
        <Boton
          variante={a.activo ? 'secundario' : 'principal'}
          disabled={cambioEstado.isPending}
          onClick={() => {
            cambioEstado.mutate(a)
          }}
        >
          {a.activo ? 'Dar de baja' : 'Activar'}
        </Boton>
      ),
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Catálogo</h1>
        <p className="mt-1 text-sm text-slate-600">
          Es opcional: se puede vender escribiendo la prenda a mano. Cargá de a poco lo
          que más se repite. Un artículo por modelo, no uno por talle — el talle se
          escribe al vender.
        </p>
      </div>

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <form
        onSubmit={(evento) => {
          evento.preventDefault()
          alta.mutate()
        }}
        className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <Campo
          etiqueta="Nombre"
          required
          placeholder="Zapatilla Nike Air"
          value={nombre}
          onChange={(evento) => setNombre(evento.target.value)}
        />
        <Campo
          etiqueta="Categoría"
          placeholder="Calzado"
          ayuda="Opcional. Sirve para agrupar."
          value={categoria}
          onChange={(evento) => setCategoria(evento.target.value)}
        />
        <Campo
          etiqueta="Precio"
          inputMode="decimal"
          required
          placeholder="0.00"
          value={precio}
          onChange={(evento) => setPrecio(evento.target.value)}
        />
        <div className="flex items-end">
          <Boton type="submit" disabled={alta.isPending}>
            Agregar
          </Boton>
        </div>
      </form>

      <Campo
        etiqueta="Buscar"
        type="search"
        placeholder="Nombre o categoría"
        value={buscar}
        onChange={(evento) => setBuscar(evento.target.value)}
      />

      <Listado
        columnas={columnas}
        filas={articulos.data ?? []}
        claveDe={(a) => a.id}
        cargando={articulos.isPending}
        vacio="Todavía no hay ningún artículo cargado."
      />

      <Ayuda pantalla="articulos" />
    </div>
  )
}
