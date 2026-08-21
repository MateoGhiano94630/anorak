/** El catálogo: todas las prendas del local. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo, Selector } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { useCategorias, useMarcas } from '../lib/catalogos'
import { ErrorApi, pedir } from '../lib/api'
import { formatearRango } from '../lib/dinero'
import { NOMBRE_GENERO, NOMBRE_TEMPORADA, opcionesDe } from '../lib/etiquetas'
import type { Genero, Producto, ProductoEnLista, Temporada } from '../lib/tipos'

const COLUMNAS: Columna<ProductoEnLista>[] = [
  {
    clave: 'nombre',
    titulo: 'Prenda',
    principal: true,
    valor: (p) => (
      <span className="flex items-center gap-3">
        {p.imagen_url !== null ? (
          <img
            src={p.imagen_url}
            alt=""
            className="size-10 rounded object-cover"
            loading="lazy"
          />
        ) : null}
        {p.nombre}
      </span>
    ),
  },
  { clave: 'categoria', titulo: 'Categoría', valor: (p) => p.categoria },
  { clave: 'marca', titulo: 'Marca', valor: (p) => p.marca ?? '—' },
  {
    clave: 'temporada',
    titulo: 'Temporada',
    valor: (p) => NOMBRE_TEMPORADA[p.temporada],
    soloTabla: true,
  },
  {
    clave: 'variantes',
    titulo: 'Talles y colores',
    valor: (p) => p.cantidad_variantes,
    alDerecha: true,
  },
  {
    clave: 'precio',
    titulo: 'Precio',
    valor: (p) => formatearRango(p.precio_desde, p.precio_hasta),
    alDerecha: true,
  },
]

export function Catalogo() {
  const navegar = useNavigate()
  const clienteConsultas = useQueryClient()
  const categorias = useCategorias()
  const marcas = useMarcas()

  const [buscar, setBuscar] = useState('')
  const [categoriaId, setCategoriaId] = useState('')
  const [mostrarAlta, setMostrarAlta] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [nombre, setNombre] = useState('')
  const [nuevaCategoria, setNuevaCategoria] = useState('')
  const [marcaId, setMarcaId] = useState('')
  const [genero, setGenero] = useState<Genero>('UNISEX')
  const [temporada, setTemporada] = useState<Temporada>('ATEMPORAL')

  const productos = useQuery({
    queryKey: ['productos', buscar, categoriaId],
    queryFn: () => {
      const parametros = new URLSearchParams()
      if (buscar.trim() !== '') parametros.set('buscar', buscar.trim())
      if (categoriaId !== '') parametros.set('categoria_id', categoriaId)
      const cola = parametros.toString()
      return pedir<ProductoEnLista[]>(`/productos${cola === '' ? '' : `?${cola}`}`)
    },
  })

  const alta = useMutation({
    mutationFn: () =>
      pedir<Producto>('/productos', {
        metodo: 'POST',
        cuerpo: {
          nombre,
          categoria_id: nuevaCategoria,
          marca_id: marcaId === '' ? null : marcaId,
          genero,
          temporada,
        },
      }),
    onSuccess: (creado) => {
      setError(null)
      void clienteConsultas.invalidateQueries({ queryKey: ['productos'] })
      // Se entra directo a la prenda recién creada: lo siguiente que hay que
      // hacer siempre es generarle los talles y colores.
      void navegar(`/catalogo/${creado.id}`)
    },
    onError: (fallo) => {
      setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo guardar.')
    },
  })

  const hayCategorias = (categorias.data ?? []).length > 0

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Catálogo</h1>
        <Boton
          onClick={() => {
            setMostrarAlta((estaba) => !estaba)
          }}
          disabled={!hayCategorias}
        >
          {mostrarAlta ? 'Cancelar' : 'Nueva prenda'}
        </Boton>
      </div>

      {!hayCategorias ? (
        <p className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
          Antes de cargar prendas hay que crear al menos una categoría, porque es la que
          dice qué talles existen.{' '}
          <Link to="/catalogos" className="underline">
            Ir a marcas, colores y categorías
          </Link>
          .
        </p>
      ) : null}

      {mostrarAlta ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault()
            alta.mutate()
          }}
          className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          <Campo
            etiqueta="Nombre de la prenda"
            required
            value={nombre}
            onChange={(evento) => setNombre(evento.target.value)}
          />
          <Selector
            etiqueta="Categoría"
            required
            value={nuevaCategoria}
            onChange={(evento) => setNuevaCategoria(evento.target.value)}
            ayuda="Define qué talles va a tener."
            opciones={[
              { valor: '', texto: 'Elegí una' },
              ...(categorias.data ?? []).map((c) => ({
                valor: c.id,
                texto: `${c.nombre} (${c.curva_nombre})`,
              })),
            ]}
          />
          <Selector
            etiqueta="Marca"
            value={marcaId}
            onChange={(evento) => setMarcaId(evento.target.value)}
            opciones={[
              { valor: '', texto: 'Sin marca' },
              ...(marcas.data ?? []).map((m) => ({ valor: m.id, texto: m.nombre })),
            ]}
          />
          <Selector
            etiqueta="Para quién es"
            value={genero}
            onChange={(evento) => setGenero(evento.target.value as Genero)}
            opciones={opcionesDe(NOMBRE_GENERO)}
          />
          <Selector
            etiqueta="Temporada"
            value={temporada}
            onChange={(evento) => setTemporada(evento.target.value as Temporada)}
            opciones={opcionesDe(NOMBRE_TEMPORADA)}
          />
          <div className="flex items-end">
            <Boton type="submit" disabled={alta.isPending}>
              Crear y cargar talles
            </Boton>
          </div>
        </form>
      ) : null}

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        <Campo
          etiqueta="Buscar"
          type="search"
          placeholder="Nombre de la prenda"
          value={buscar}
          onChange={(evento) => setBuscar(evento.target.value)}
        />
        <Selector
          etiqueta="Categoría"
          value={categoriaId}
          onChange={(evento) => setCategoriaId(evento.target.value)}
          opciones={[
            { valor: '', texto: 'Todas' },
            ...(categorias.data ?? []).map((c) => ({ valor: c.id, texto: c.nombre })),
          ]}
        />
      </div>

      <Listado
        columnas={COLUMNAS}
        filas={productos.data ?? []}
        claveDe={(fila) => fila.id}
        cargando={productos.isPending}
        vacio={
          buscar.trim() === ''
            ? 'Todavía no hay prendas cargadas.'
            : 'Ninguna prenda coincide con lo que buscaste.'
        }
        alTocarFila={(fila) => {
          void navegar(`/catalogo/${fila.id}`)
        }}
      />

      <Ayuda pantalla="catalogo" />
    </div>
  )
}
