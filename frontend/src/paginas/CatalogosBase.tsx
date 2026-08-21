/** Marcas, colores, categorías y curvas de talle: las listas del catálogo. */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo, Selector } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { ErrorApi, pedir } from '../lib/api'
import { useCategorias, useColores, useCurvas, useMarcas } from '../lib/catalogos'
import type { Categoria, Color, CurvaTalle, Marca } from '../lib/tipos'

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-medium text-slate-900">{titulo}</h2>
      {children}
    </section>
  )
}

export function CatalogosBase() {
  const clienteConsultas = useQueryClient()
  const marcas = useMarcas()
  const colores = useColores()
  const categorias = useCategorias()
  const curvas = useCurvas()

  const [error, setError] = useState<string | null>(null)
  const [nombreMarca, setNombreMarca] = useState('')
  const [nombreColor, setNombreColor] = useState('')
  const [tonoColor, setTonoColor] = useState('#000000')
  const [nombreCurva, setNombreCurva] = useState('')
  const [tallesCurva, setTallesCurva] = useState('')
  const [nombreCategoria, setNombreCategoria] = useState('')
  const [curvaCategoria, setCurvaCategoria] = useState('')

  function refrescar(clave: string): void {
    setError(null)
    void clienteConsultas.invalidateQueries({ queryKey: [clave] })
  }

  function avisar(fallo: unknown): void {
    setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo guardar.')
  }

  const altaMarca = useMutation({
    mutationFn: () =>
      pedir<Marca>('/marcas', { metodo: 'POST', cuerpo: { nombre: nombreMarca } }),
    onSuccess: () => {
      setNombreMarca('')
      refrescar('marcas')
    },
    onError: avisar,
  })

  const altaColor = useMutation({
    mutationFn: () =>
      pedir<Color>('/colores', {
        metodo: 'POST',
        cuerpo: { nombre: nombreColor, codigo_hex: tonoColor.toUpperCase() },
      }),
    onSuccess: () => {
      setNombreColor('')
      refrescar('colores')
    },
    onError: avisar,
  })

  const altaCurva = useMutation({
    mutationFn: () =>
      pedir<CurvaTalle>('/curvas-talle', {
        metodo: 'POST',
        cuerpo: {
          nombre: nombreCurva,
          // Se escriben separados por coma y en el orden en que van: S, M, L,
          // XL. El orden de carga es el que después ve el mostrador.
          talles: tallesCurva
            .split(',')
            .map((valor) => valor.trim())
            .filter((valor) => valor !== '')
            .map((valor) => ({ valor, orden: 0 })),
        },
      }),
    onSuccess: () => {
      setNombreCurva('')
      setTallesCurva('')
      refrescar('curvas-talle')
    },
    onError: avisar,
  })

  const altaCategoria = useMutation({
    mutationFn: () =>
      pedir<Categoria>('/categorias', {
        metodo: 'POST',
        cuerpo: { nombre: nombreCategoria, curva_talle_id: curvaCategoria },
      }),
    onSuccess: () => {
      setNombreCategoria('')
      refrescar('categorias')
    },
    onError: avisar,
  })

  const columnasMarca: Columna<Marca>[] = [
    { clave: 'nombre', titulo: 'Marca', valor: (m) => m.nombre, principal: true },
    {
      clave: 'estado',
      titulo: 'Estado',
      valor: (m) => (m.activa ? 'En uso' : 'Sin usar'),
    },
  ]

  const columnasColor: Columna<Color>[] = [
    {
      clave: 'nombre',
      titulo: 'Color',
      principal: true,
      valor: (c) => (
        <span className="flex items-center gap-2">
          {c.codigo_hex !== null ? (
            <span
              aria-hidden="true"
              style={{ backgroundColor: c.codigo_hex }}
              className="size-4 rounded-full border border-slate-400"
            />
          ) : null}
          {c.nombre}
        </span>
      ),
    },
    {
      clave: 'estado',
      titulo: 'Estado',
      valor: (c) => (c.activo ? 'En uso' : 'Sin usar'),
    },
  ]

  const columnasCurva: Columna<CurvaTalle>[] = [
    { clave: 'nombre', titulo: 'Curva', valor: (c) => c.nombre, principal: true },
    {
      clave: 'talles',
      titulo: 'Talles',
      valor: (c) => c.talles.map((t) => t.valor).join(' · '),
    },
  ]

  const columnasCategoria: Columna<Categoria>[] = [
    { clave: 'nombre', titulo: 'Categoría', valor: (c) => c.nombre, principal: true },
    { clave: 'curva', titulo: 'Usa los talles de', valor: (c) => c.curva_nombre },
  ]

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Marcas, colores y categorías</h1>

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <Seccion titulo="Curvas de talle">
        <p className="text-sm text-slate-600">
          El conjunto de talles que van juntos. Escribilos separados por coma, en el orden
          en el que se piden en el mostrador.
        </p>
        <form
          onSubmit={(evento) => {
            evento.preventDefault()
            altaCurva.mutate()
          }}
          className="grid gap-4 sm:grid-cols-3"
        >
          <Campo
            etiqueta="Nombre"
            required
            placeholder="Remeras"
            value={nombreCurva}
            onChange={(evento) => setNombreCurva(evento.target.value)}
          />
          <Campo
            etiqueta="Talles"
            required
            placeholder="S, M, L, XL"
            value={tallesCurva}
            onChange={(evento) => setTallesCurva(evento.target.value)}
          />
          <div className="flex items-end">
            <Boton type="submit" disabled={altaCurva.isPending}>
              Agregar curva
            </Boton>
          </div>
        </form>
        <Listado
          columnas={columnasCurva}
          filas={curvas.data ?? []}
          claveDe={(c) => c.id}
          cargando={curvas.isPending}
          vacio="Todavía no hay ninguna curva de talles."
        />
      </Seccion>

      <Seccion titulo="Categorías">
        <form
          onSubmit={(evento) => {
            evento.preventDefault()
            altaCategoria.mutate()
          }}
          className="grid gap-4 sm:grid-cols-3"
        >
          <Campo
            etiqueta="Nombre"
            required
            placeholder="Remeras"
            value={nombreCategoria}
            onChange={(evento) => setNombreCategoria(evento.target.value)}
          />
          <Selector
            etiqueta="Talles que usa"
            required
            value={curvaCategoria}
            onChange={(evento) => setCurvaCategoria(evento.target.value)}
            opciones={[
              { valor: '', texto: 'Elegí una curva' },
              ...(curvas.data ?? []).map((c) => ({ valor: c.id, texto: c.nombre })),
            ]}
          />
          <div className="flex items-end">
            <Boton type="submit" disabled={altaCategoria.isPending}>
              Agregar categoría
            </Boton>
          </div>
        </form>
        <Listado
          columnas={columnasCategoria}
          filas={categorias.data ?? []}
          claveDe={(c) => c.id}
          cargando={categorias.isPending}
          vacio="Todavía no hay ninguna categoría."
        />
      </Seccion>

      <Seccion titulo="Marcas">
        <form
          onSubmit={(evento) => {
            evento.preventDefault()
            altaMarca.mutate()
          }}
          className="flex flex-col gap-4 sm:flex-row sm:items-end"
        >
          <div className="flex-1">
            <Campo
              etiqueta="Nombre"
              required
              value={nombreMarca}
              onChange={(evento) => setNombreMarca(evento.target.value)}
            />
          </div>
          <Boton type="submit" disabled={altaMarca.isPending}>
            Agregar marca
          </Boton>
        </form>
        <Listado
          columnas={columnasMarca}
          filas={marcas.data ?? []}
          claveDe={(m) => m.id}
          cargando={marcas.isPending}
          vacio="Todavía no hay ninguna marca."
        />
      </Seccion>

      <Seccion titulo="Colores">
        <form
          onSubmit={(evento) => {
            evento.preventDefault()
            altaColor.mutate()
          }}
          className="flex flex-col gap-4 sm:flex-row sm:items-end"
        >
          <div className="flex-1">
            <Campo
              etiqueta="Nombre"
              required
              value={nombreColor}
              onChange={(evento) => setNombreColor(evento.target.value)}
            />
          </div>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-slate-700">Tono</span>
            <input
              type="color"
              value={tonoColor}
              onChange={(evento) => setTonoColor(evento.target.value)}
              className="h-11 w-20 rounded-lg border border-slate-300 bg-white"
            />
          </label>
          <Boton type="submit" disabled={altaColor.isPending}>
            Agregar color
          </Boton>
        </form>
        <Listado
          columnas={columnasColor}
          filas={colores.data ?? []}
          claveDe={(c) => c.id}
          cargando={colores.isPending}
          vacio="Todavía no hay ningún color."
        />
      </Seccion>

      <Ayuda pantalla="catalogosBase" />
    </div>
  )
}
