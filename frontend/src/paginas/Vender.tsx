/** El mostrador: se arma la venta, se cobra y se registra. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo } from '../componentes/Campo'
import { ErrorApi, pedir } from '../lib/api'
import {
  aImporte,
  faltaCobrar,
  subtotalDeLinea,
  totalesDelCarrito,
  vuelto,
} from '../lib/carrito'
import { formatearPesos } from '../lib/dinero'
import type {
  Articulo,
  LineaDelCarrito,
  MedioPago,
  SesionCaja,
  Venta,
} from '../lib/tipos'

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-medium text-slate-900">{titulo}</h2>
      {children}
    </section>
  )
}

export function Vender() {
  const clienteConsultas = useQueryClient()
  const [lineas, setLineas] = useState<LineaDelCarrito[]>([])
  const [descuento, setDescuento] = useState('')
  const [importes, setImportes] = useState<Record<string, string>>({})
  const [entregado, setEntregado] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [hecha, setHecha] = useState<Venta | null>(null)

  const caja = useQuery({
    queryKey: ['caja'],
    queryFn: () => pedir<SesionCaja | null>('/caja/actual'),
  })
  const medios = useQuery({
    queryKey: ['medios-pago'],
    queryFn: () => pedir<MedioPago[]>('/medios-pago'),
  })

  const activos = (medios.data ?? []).filter((medio) => medio.activo)
  const efectivo = activos.find((medio) => medio.afecta_efectivo)
  const totales = totalesDelCarrito(lineas, descuento)
  const falta = faltaCobrar(
    totales.total,
    activos.map((medio) => importes[medio.id] ?? ''),
  )
  const vueltoACobrar = vuelto(entregado, efectivo ? (importes[efectivo.id] ?? '') : '')

  function limpiar(): void {
    setLineas([])
    setDescuento('')
    setImportes({})
    setEntregado('')
    setError(null)
  }

  const registrar = useMutation({
    mutationFn: () =>
      pedir<Venta>('/ventas', {
        metodo: 'POST',
        cuerpo: {
          lineas: lineas.map((linea) => ({
            articulo_id: linea.articulo_id,
            descripcion: linea.descripcion,
            talle: linea.talle === '' ? null : linea.talle,
            cantidad: linea.cantidad,
            precio_unitario: linea.precio_unitario === '' ? '0' : linea.precio_unitario,
            descuento: linea.descuento === '' ? '0' : linea.descuento,
          })),
          pagos: activos
            .filter((medio) => (importes[medio.id] ?? '') !== '')
            .map((medio) => ({
              medio_pago_id: medio.id,
              importe: importes[medio.id] ?? '0',
            })),
          descuento: descuento === '' ? '0' : descuento,
        },
      }),
    onSuccess: (venta) => {
      setHecha(venta)
      limpiar()
      void clienteConsultas.invalidateQueries({ queryKey: ['caja'] })
      void clienteConsultas.invalidateQueries({ queryKey: ['ventas'] })
    },
    onError: (fallo) => {
      setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo registrar.')
    },
  })

  if (caja.isPending) return <p className="text-slate-500">Cargando…</p>

  if (caja.data === null) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-xl font-semibold">Vender</h1>
        <p className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
          La caja está cerrada, así que todavía no se puede vender. Toda venta pertenece a
          la caja del día: es lo que hace que al cerrar los números cuadren.{' '}
          <Link to="/caja" className="underline">
            Abrir la caja
          </Link>
          .
        </p>
        <Ayuda pantalla="vender" />
      </div>
    )
  }

  if (hecha !== null) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-xl font-semibold">Venta registrada</h1>
        <Seccion titulo={`Venta #${hecha.numero}`}>
          <p className="text-2xl tabular-nums">{formatearPesos(hecha.total)}</p>
          <ul className="flex flex-col gap-1 text-sm text-slate-700">
            {hecha.lineas.map((linea) => (
              <li key={linea.id} className="flex justify-between gap-4">
                <span>
                  {linea.cantidad} × {linea.descripcion}
                  {linea.talle !== null ? ` · talle ${linea.talle}` : ''}
                </span>
                <span className="tabular-nums">{formatearPesos(linea.subtotal)}</span>
              </li>
            ))}
          </ul>
          <p className="text-sm text-slate-600">
            Cobrado con {hecha.cobros.map((cobro) => cobro.medio_pago).join(' y ')}.
          </p>
          <div className="flex gap-2">
            <Boton
              onClick={() => {
                setHecha(null)
              }}
            >
              Otra venta
            </Boton>
            <Link to="/ventas" className="flex items-center text-sm underline">
              Ver todas las ventas
            </Link>
          </div>
        </Seccion>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Vender</h1>

      {error !== null ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <AgregarLinea
        alAgregar={(linea) => {
          setLineas((estaban) => [...estaban, linea])
          setError(null)
        }}
      />

      <Seccion titulo="Lo que se lleva">
        {lineas.length === 0 ? (
          <p className="text-sm text-slate-500">
            Todavía no agregaste nada. Buscá en el catálogo o escribilo a mano.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {lineas.map((linea) => (
              <li
                key={linea.clave}
                className="grid gap-3 rounded-lg border border-slate-200 p-3 sm:grid-cols-2 lg:grid-cols-6"
              >
                <p className="self-center font-medium lg:col-span-2">
                  {linea.descripcion}
                </p>
                <Campo
                  etiqueta="Talle"
                  value={linea.talle}
                  onChange={(evento) => {
                    setLineas((estaban) =>
                      estaban.map((otra) =>
                        otra.clave === linea.clave
                          ? { ...otra, talle: evento.target.value }
                          : otra,
                      ),
                    )
                  }}
                />
                <Campo
                  etiqueta="Cantidad"
                  inputMode="numeric"
                  value={String(linea.cantidad)}
                  onChange={(evento) => {
                    const cantidad = Math.max(Number(evento.target.value) || 1, 1)
                    setLineas((estaban) =>
                      estaban.map((otra) =>
                        otra.clave === linea.clave ? { ...otra, cantidad } : otra,
                      ),
                    )
                  }}
                />
                <Campo
                  etiqueta="Precio unitario"
                  inputMode="decimal"
                  value={linea.precio_unitario}
                  onChange={(evento) => {
                    setLineas((estaban) =>
                      estaban.map((otra) =>
                        otra.clave === linea.clave
                          ? { ...otra, precio_unitario: evento.target.value }
                          : otra,
                      ),
                    )
                  }}
                />
                <Campo
                  etiqueta="Descuento"
                  inputMode="decimal"
                  placeholder="0.00"
                  value={linea.descuento}
                  onChange={(evento) => {
                    setLineas((estaban) =>
                      estaban.map((otra) =>
                        otra.clave === linea.clave
                          ? { ...otra, descuento: evento.target.value }
                          : otra,
                      ),
                    )
                  }}
                />
                <div className="flex items-center justify-between gap-3 sm:col-span-2 lg:col-span-6">
                  <span className="tabular-nums text-slate-700">
                    {formatearPesos(aImporte(subtotalDeLinea(linea)))}
                  </span>
                  <Boton
                    variante="secundario"
                    onClick={() => {
                      setLineas((estaban) =>
                        estaban.filter((otra) => otra.clave !== linea.clave),
                      )
                    }}
                  >
                    Quitar
                  </Boton>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Seccion>

      {lineas.length > 0 ? (
        <Seccion titulo="Cobrar">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo
              etiqueta="Descuento sobre el total"
              inputMode="decimal"
              placeholder="0.00"
              ayuda="Además de los descuentos de cada línea."
              value={descuento}
              onChange={(evento) => setDescuento(evento.target.value)}
            />
            <dl className="self-end">
              <div className="flex justify-between gap-4 text-sm text-slate-600">
                <dt>Suma de las líneas</dt>
                <dd className="tabular-nums">
                  {formatearPesos(aImporte(totales.subtotal))}
                </dd>
              </div>
              <div className="flex justify-between gap-4 text-lg font-medium">
                <dt>Total a cobrar</dt>
                <dd className="tabular-nums">
                  {formatearPesos(aImporte(totales.total))}
                </dd>
              </div>
            </dl>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {activos.map((medio) => (
              <Campo
                key={medio.id}
                etiqueta={medio.nombre}
                inputMode="decimal"
                placeholder="0.00"
                value={importes[medio.id] ?? ''}
                onChange={(evento) => {
                  setImportes((estaban) => ({
                    ...estaban,
                    [medio.id]: evento.target.value,
                  }))
                }}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {efectivo !== undefined ? (
              <Boton
                variante="secundario"
                onClick={() => {
                  setImportes({ [efectivo.id]: aImporte(totales.total) })
                }}
              >
                Todo en efectivo
              </Boton>
            ) : null}
            <p className={`text-sm ${falta === 0 ? 'text-green-800' : 'text-amber-700'}`}>
              {falta === 0
                ? 'La venta está cubierta.'
                : falta > 0
                  ? `Falta cobrar ${formatearPesos(aImporte(falta))}.`
                  : `Estás cobrando ${formatearPesos(aImporte(-falta))} de más.`}
            </p>
          </div>

          {efectivo !== undefined && (importes[efectivo.id] ?? '') !== '' ? (
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo
                etiqueta="Con cuánto paga"
                inputMode="decimal"
                placeholder="0.00"
                ayuda="Solo para calcular el vuelto. No se guarda."
                value={entregado}
                onChange={(evento) => setEntregado(evento.target.value)}
              />
              <p className="self-end text-lg">
                Vuelto:{' '}
                <span className="font-medium tabular-nums">
                  {formatearPesos(aImporte(vueltoACobrar))}
                </span>
              </p>
            </div>
          ) : null}

          <div>
            <Boton
              disabled={falta !== 0 || totales.total === 0 || registrar.isPending}
              onClick={() => {
                registrar.mutate()
              }}
            >
              Registrar la venta
            </Boton>
          </div>
        </Seccion>
      ) : null}

      <Ayuda pantalla="vender" />
    </div>
  )
}

/** Buscador del catálogo y carga de una línea escrita a mano. */
function AgregarLinea({ alAgregar }: { alAgregar: (linea: LineaDelCarrito) => void }) {
  const [buscar, setBuscar] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [precio, setPrecio] = useState('')

  const articulos = useQuery({
    queryKey: ['articulos', buscar],
    queryFn: () => {
      const cola =
        buscar.trim() === '' ? '' : `?buscar=${encodeURIComponent(buscar.trim())}`
      return pedir<Articulo[]>(`/articulos${cola}`)
    },
  })

  function nueva(campos: Partial<LineaDelCarrito>): LineaDelCarrito {
    return {
      // Clave local para dibujar la lista: la venta todavía no existe.
      clave: crypto.randomUUID(),
      articulo_id: null,
      descripcion: '',
      talle: '',
      cantidad: 1,
      precio_unitario: '',
      descuento: '',
      ...campos,
    }
  }

  return (
    <Seccion titulo="Agregar al carrito">
      <Campo
        etiqueta="Buscar en el catálogo"
        type="search"
        placeholder="Zapatilla, campera…"
        value={buscar}
        onChange={(evento) => setBuscar(evento.target.value)}
      />
      {(articulos.data ?? []).length > 0 ? (
        <ul className="flex flex-wrap gap-2">
          {(articulos.data ?? []).slice(0, 12).map((articulo) => (
            <li key={articulo.id}>
              <Boton
                variante="secundario"
                onClick={() => {
                  alAgregar(
                    nueva({
                      articulo_id: articulo.id,
                      descripcion: articulo.nombre,
                      precio_unitario: articulo.precio,
                    }),
                  )
                }}
              >
                {articulo.nombre} · {formatearPesos(articulo.precio)}
              </Boton>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">
          {buscar.trim() === ''
            ? 'El catálogo está vacío. Podés vender escribiendo la prenda a mano.'
            : 'Ningún artículo coincide. Escribilo a mano acá abajo.'}
        </p>
      )}

      <form
        onSubmit={(evento) => {
          evento.preventDefault()
          alAgregar(nueva({ descripcion: descripcion.trim(), precio_unitario: precio }))
          setDescripcion('')
          setPrecio('')
        }}
        className="flex flex-col gap-4 border-t border-slate-200 pt-4 sm:flex-row sm:items-end"
      >
        <div className="flex-1">
          <Campo
            etiqueta="Prenda escrita a mano"
            required
            placeholder="Campera de abrigo"
            value={descripcion}
            onChange={(evento) => setDescripcion(evento.target.value)}
          />
        </div>
        <div className="sm:w-40">
          <Campo
            etiqueta="Precio de la prenda"
            inputMode="decimal"
            required
            placeholder="0.00"
            value={precio}
            onChange={(evento) => setPrecio(evento.target.value)}
          />
        </div>
        <Boton type="submit">Agregar</Boton>
      </form>
    </Seccion>
  )
}
