/** Una prenda: sus talles y colores, sus códigos, sus precios y sus fotos. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { SeleccionMultiple } from '../componentes/SeleccionMultiple'
import { useSesion } from '../contexto/sesion'
import { ErrorApi, pedir, subirArchivo } from '../lib/api'
import { useCategorias, useColores, useCurvas } from '../lib/catalogos'
import { formatearPesos } from '../lib/dinero'
import { formatearFechaHora } from '../lib/fecha'
import { NOMBRE_GENERO, NOMBRE_TEMPORADA } from '../lib/etiquetas'
import type { ImagenProducto, Precio, Producto, Variante } from '../lib/tipos'

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-medium text-slate-900">{titulo}</h2>
      {children}
    </section>
  )
}

export function ProductoDetalle() {
  const { productoId = '' } = useParams()
  const clienteConsultas = useQueryClient()
  const { usuario } = useSesion()
  const esAdmin = usuario?.rol === 'ADMIN'

  const colores = useColores()
  const curvas = useCurvas()
  const categorias = useCategorias()

  const [talleIds, setTalleIds] = useState<string[]>([])
  const [colorIds, setColorIds] = useState<string[]>([])
  const [precio, setPrecio] = useState('')
  const [costo, setCosto] = useState('')
  const [motivo, setMotivo] = useState('')
  const [varianteAbierta, setVarianteAbierta] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const producto = useQuery({
    queryKey: ['producto', productoId],
    queryFn: () => pedir<Producto>(`/productos/${productoId}`),
  })

  function refrescar(): void {
    setError(null)
    void clienteConsultas.invalidateQueries({ queryKey: ['producto', productoId] })
    void clienteConsultas.invalidateQueries({ queryKey: ['productos'] })
  }

  function avisar(fallo: unknown): void {
    setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo completar.')
  }

  const generar = useMutation({
    mutationFn: () =>
      pedir<Producto>(`/productos/${productoId}/variantes`, {
        metodo: 'POST',
        cuerpo: { talle_ids: talleIds, color_ids: colorIds },
      }),
    onSuccess: () => {
      setTalleIds([])
      setColorIds([])
      refrescar()
    },
    onError: avisar,
  })

  const ponerPrecio = useMutation({
    mutationFn: () =>
      pedir<Precio[]>(`/productos/${productoId}/precio`, {
        metodo: 'POST',
        cuerpo: {
          precio_venta: precio,
          costo: costo === '' ? null : costo,
          motivo: motivo === '' ? null : motivo,
        },
      }),
    onSuccess: () => {
      setPrecio('')
      setCosto('')
      setMotivo('')
      refrescar()
    },
    onError: avisar,
  })

  const subirFoto = useMutation({
    mutationFn: (archivo: File) =>
      subirArchivo<ImagenProducto>(`/productos/${productoId}/imagenes`, archivo),
    onSuccess: refrescar,
    onError: avisar,
  })

  const borrarFoto = useMutation({
    mutationFn: (imagenId: string) =>
      // `undefined` y no `void`: al borrar, la API contesta 204 sin cuerpo,
      // que es exactamente lo que devuelve `pedir` en ese caso.
      pedir<undefined>(`/productos/imagenes/${imagenId}`, { metodo: 'DELETE' }),
    onSuccess: refrescar,
    onError: avisar,
  })

  if (producto.isPending) return <p className="text-slate-500">Cargando…</p>
  if (producto.data === undefined) {
    return <p className="text-red-700">No se encontró la prenda.</p>
  }

  const datos = producto.data
  const categoria = (categorias.data ?? []).find((c) => c.id === datos.categoria_id)
  const curva = (curvas.data ?? []).find((c) => c.id === categoria?.curva_talle_id)

  const columnas: Columna<Variante>[] = [
    {
      clave: 'prenda',
      titulo: 'Talle y color',
      principal: true,
      valor: (v) => (
        <span className="flex items-center gap-2">
          {v.codigo_hex !== null ? (
            <span
              aria-hidden="true"
              style={{ backgroundColor: v.codigo_hex }}
              className="size-4 rounded-full border border-slate-400"
            />
          ) : null}
          {v.talle} · {v.color}
        </span>
      ),
    },
    { clave: 'sku', titulo: 'Código', valor: (v) => v.sku },
    {
      clave: 'barras',
      titulo: 'Código de barras',
      valor: (v) => v.codigo_barras ?? '—',
      soloTabla: true,
    },
    {
      clave: 'precio',
      titulo: 'Precio',
      alDerecha: true,
      valor: (v) =>
        v.precio_venta === null ? (
          <span className="text-amber-700">Sin precio</span>
        ) : (
          formatearPesos(v.precio_venta)
        ),
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to="/catalogo" className="text-sm text-slate-600 underline">
          Volver al catálogo
        </Link>
        <h1 className="mt-2 text-xl font-semibold">{datos.nombre}</h1>
        <p className="text-sm text-slate-600">
          {datos.categoria}
          {datos.marca !== null ? ` · ${datos.marca}` : ''} ·{' '}
          {NOMBRE_GENERO[datos.genero]} · {NOMBRE_TEMPORADA[datos.temporada]}
        </p>
      </div>

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <Seccion titulo="Talles y colores">
        <Listado
          columnas={columnas}
          filas={datos.variantes}
          claveDe={(v) => v.id}
          vacio="Esta prenda todavía no tiene talles ni colores cargados."
          alTocarFila={(v) => {
            setVarianteAbierta((abierta) => (abierta === v.id ? null : v.id))
          }}
        />
        {varianteAbierta !== null ? (
          <DetalleVariante
            // La clave hace que el panel se rearme al cambiar de talle. Sin
            // ella, React reusa el mismo y el código de barras que quedó
            // escrito para una prenda aparece cargado en la siguiente.
            key={varianteAbierta}
            variante={datos.variantes.find((v) => v.id === varianteAbierta)}
            esAdmin={esAdmin}
            alGuardar={refrescar}
            alFallar={avisar}
          />
        ) : null}
      </Seccion>

      <Seccion titulo="Agregar talles y colores">
        <SeleccionMultiple
          etiqueta={`Talles${curva !== undefined ? ` (${curva.nombre})` : ''}`}
          opciones={(curva?.talles ?? []).map((t) => ({ valor: t.id, texto: t.valor }))}
          seleccionados={talleIds}
          alCambiar={setTalleIds}
          vacio="La categoría de esta prenda no tiene talles cargados."
        />
        <SeleccionMultiple
          etiqueta="Colores"
          opciones={(colores.data ?? []).map((c) => ({
            valor: c.id,
            texto: c.nombre,
            colorHex: c.codigo_hex,
          }))}
          seleccionados={colorIds}
          alCambiar={setColorIds}
        />
        <div>
          <Boton
            disabled={talleIds.length === 0 || colorIds.length === 0 || generar.isPending}
            onClick={() => {
              generar.mutate()
            }}
          >
            Generar {talleIds.length * colorIds.length || ''} combinaciones
          </Boton>
        </div>
      </Seccion>

      {esAdmin ? (
        <Seccion titulo="Poner precio a toda la prenda">
          <form
            onSubmit={(evento) => {
              evento.preventDefault()
              ponerPrecio.mutate()
            }}
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
          >
            <Campo
              etiqueta="Precio de venta"
              inputMode="decimal"
              required
              placeholder="0.00"
              value={precio}
              onChange={(evento) => setPrecio(evento.target.value)}
            />
            <Campo
              etiqueta="Costo"
              inputMode="decimal"
              placeholder="0.00"
              ayuda="Opcional. Es lo que permite ver el margen."
              value={costo}
              onChange={(evento) => setCosto(evento.target.value)}
            />
            <Campo
              etiqueta="Motivo"
              placeholder="Lista nueva del proveedor"
              value={motivo}
              onChange={(evento) => setMotivo(evento.target.value)}
            />
            <div className="flex items-end">
              <Boton
                type="submit"
                disabled={datos.variantes.length === 0 || ponerPrecio.isPending}
              >
                Guardar precio
              </Boton>
            </div>
          </form>
        </Seccion>
      ) : null}

      <Seccion titulo="Fotos">
        <div className="flex flex-wrap gap-3">
          {datos.imagenes.map((imagen) => (
            <figure key={imagen.id} className="flex flex-col gap-1">
              {imagen.url !== null ? (
                <img
                  src={imagen.url}
                  alt=""
                  className="size-28 rounded-lg object-cover"
                />
              ) : (
                <span className="flex size-28 items-center justify-center rounded-lg bg-slate-100 text-xs text-slate-500">
                  Sin vista
                </span>
              )}
              <Boton
                variante="secundario"
                onClick={() => {
                  borrarFoto.mutate(imagen.id)
                }}
              >
                Quitar
              </Boton>
            </figure>
          ))}
        </div>
        <label className="flex w-fit cursor-pointer flex-col gap-1">
          <span className="text-sm font-medium text-slate-700">Agregar una foto</span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="text-base"
            onChange={(evento) => {
              const archivo = evento.target.files?.[0]
              if (archivo !== undefined) subirFoto.mutate(archivo)
              evento.target.value = ''
            }}
          />
          <span className="text-xs text-slate-500">JPG, PNG o WEBP, hasta 3 MB.</span>
        </label>
      </Seccion>

      <Ayuda pantalla="producto" />
    </div>
  )
}

interface DetalleVarianteProps {
  variante: Variante | undefined
  esAdmin: boolean
  alGuardar: () => void
  alFallar: (fallo: unknown) => void
}

/** El panel que se abre al tocar un talle: códigos, precio e historial. */
function DetalleVariante({
  variante,
  esAdmin,
  alGuardar,
  alFallar,
}: DetalleVarianteProps) {
  const [codigoBarras, setCodigoBarras] = useState(variante?.codigo_barras ?? '')
  const [precio, setPrecio] = useState('')

  const historial = useQuery({
    queryKey: ['precios', variante?.id],
    queryFn: () => pedir<Precio[]>(`/variantes/${variante?.id ?? ''}/precios`),
    enabled: variante !== undefined,
  })

  const guardarCodigo = useMutation({
    mutationFn: () =>
      pedir<Variante>(`/variantes/${variante?.id ?? ''}`, {
        metodo: 'PATCH',
        cuerpo: { codigo_barras: codigoBarras === '' ? null : codigoBarras },
      }),
    onSuccess: alGuardar,
    onError: alFallar,
  })

  const guardarPrecio = useMutation({
    mutationFn: () =>
      pedir<Precio>(`/variantes/${variante?.id ?? ''}/precio`, {
        metodo: 'POST',
        cuerpo: { precio_venta: precio },
      }),
    onSuccess: () => {
      setPrecio('')
      alGuardar()
    },
    onError: alFallar,
  })

  if (variante === undefined) return null

  return (
    <div className="flex flex-col gap-4 rounded-lg bg-slate-50 p-4">
      <p className="text-sm font-medium">
        {variante.talle} · {variante.color} — código {variante.sku}
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Campo
              etiqueta="Código de barras"
              value={codigoBarras}
              ayuda="El de la etiqueta del proveedor, si la trae."
              onChange={(evento) => setCodigoBarras(evento.target.value)}
            />
          </div>
          <Boton
            variante="secundario"
            onClick={() => {
              guardarCodigo.mutate()
            }}
          >
            Guardar
          </Boton>
        </div>

        {esAdmin ? (
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Campo
                etiqueta="Precio solo para este talle"
                inputMode="decimal"
                placeholder="0.00"
                value={precio}
                onChange={(evento) => setPrecio(evento.target.value)}
              />
            </div>
            <Boton
              variante="secundario"
              disabled={precio === ''}
              onClick={() => {
                guardarPrecio.mutate()
              }}
            >
              Guardar
            </Boton>
          </div>
        ) : null}
      </div>

      <div>
        <p className="text-sm font-medium text-slate-700">Precios anteriores</p>
        {(historial.data ?? []).length === 0 ? (
          <p className="text-sm text-slate-500">Todavía no tuvo ningún precio.</p>
        ) : (
          <ul className="mt-1 flex flex-col gap-1 text-sm text-slate-700">
            {(historial.data ?? []).map((fila) => (
              <li key={fila.id} className="flex flex-wrap justify-between gap-2">
                <span>
                  {formatearPesos(fila.precio_venta)}
                  {fila.motivo !== null ? ` — ${fila.motivo}` : ''}
                </span>
                <span className="text-slate-500">
                  desde {formatearFechaHora(fila.vigente_desde)}
                  {fila.vigente_hasta !== null
                    ? ` hasta ${formatearFechaHora(fila.vigente_hasta)}`
                    : ' (vigente)'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
