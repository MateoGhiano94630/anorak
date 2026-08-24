/** Con qué se puede cobrar, y qué pasa con cada medio después. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Ayuda } from '../componentes/Ayuda'
import { Boton } from '../componentes/Boton'
import { Campo, Selector } from '../componentes/Campo'
import { Listado, type Columna } from '../componentes/Listado'
import { ErrorApi, pedir } from '../lib/api'
import { NOMBRE_MEDIO_PAGO, opcionesDe } from '../lib/etiquetas'
import type { MedioPago, TipoMedioPago } from '../lib/tipos'

const COLUMNAS: Columna<MedioPago>[] = [
  { clave: 'nombre', titulo: 'Medio', valor: (m) => m.nombre, principal: true },
  { clave: 'tipo', titulo: 'Tipo', valor: (m) => NOMBRE_MEDIO_PAGO[m.tipo] },
  {
    clave: 'cajon',
    titulo: '¿Queda en el cajón?',
    valor: (m) => (m.afecta_efectivo ? 'Sí, se cuenta al cerrar' : 'No, va a la cuenta'),
  },
  {
    clave: 'comision',
    titulo: 'Comisión',
    alDerecha: true,
    valor: (m) => (m.comision_porcentaje === null ? '—' : `${m.comision_porcentaje} %`),
    soloTabla: true,
  },
  {
    clave: 'dias',
    titulo: 'Acredita en',
    alDerecha: true,
    valor: (m) =>
      m.dias_acreditacion === null
        ? '—'
        : m.dias_acreditacion === 0
          ? 'El día'
          : `${m.dias_acreditacion} días`,
    soloTabla: true,
  },
  {
    clave: 'estado',
    titulo: 'Estado',
    valor: (m) => (m.activo ? 'En uso' : 'Sin usar'),
  },
]

export function MediosPago() {
  const clienteConsultas = useQueryClient()
  const [nombre, setNombre] = useState('')
  const [tipo, setTipo] = useState<TipoMedioPago>('TARJETA_DEBITO')
  const [comision, setComision] = useState('')
  const [dias, setDias] = useState('')
  const [error, setError] = useState<string | null>(null)

  const medios = useQuery({
    queryKey: ['medios-pago'],
    queryFn: () => pedir<MedioPago[]>('/medios-pago'),
  })

  const alta = useMutation({
    mutationFn: () =>
      pedir<MedioPago>('/medios-pago', {
        metodo: 'POST',
        cuerpo: {
          nombre,
          tipo,
          // Solo el efectivo queda en el cajón. Es lo que separa lo que se
          // cuenta al cerrar de lo que acredita días después en la cuenta.
          afecta_efectivo: tipo === 'EFECTIVO',
          comision_porcentaje: comision === '' ? null : comision,
          dias_acreditacion: dias === '' ? null : Number(dias),
        },
      }),
    onSuccess: () => {
      setNombre('')
      setComision('')
      setDias('')
      setError(null)
      void clienteConsultas.invalidateQueries({ queryKey: ['medios-pago'] })
    },
    onError: (fallo) => {
      setError(fallo instanceof ErrorApi ? fallo.message : 'No se pudo guardar.')
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Medios de pago</h1>

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
        className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-5"
      >
        <Campo
          etiqueta="Nombre"
          required
          placeholder="Débito Visa"
          value={nombre}
          onChange={(evento) => setNombre(evento.target.value)}
        />
        <Selector
          etiqueta="Tipo"
          value={tipo}
          onChange={(evento) => setTipo(evento.target.value as TipoMedioPago)}
          opciones={opcionesDe(NOMBRE_MEDIO_PAGO)}
        />
        <Campo
          etiqueta="Comisión"
          inputMode="decimal"
          placeholder="1.80"
          ayuda="En por ciento. Con los números de tu contrato."
          value={comision}
          onChange={(evento) => setComision(evento.target.value)}
        />
        <Campo
          etiqueta="Días para acreditar"
          inputMode="numeric"
          placeholder="18"
          value={dias}
          onChange={(evento) => setDias(evento.target.value)}
        />
        <div className="flex items-end">
          <Boton type="submit" disabled={alta.isPending}>
            Agregar
          </Boton>
        </div>
      </form>

      <Listado
        columnas={COLUMNAS}
        filas={medios.data ?? []}
        claveDe={(m) => m.id}
        cargando={medios.isPending}
        vacio="Todavía no hay ningún medio de pago cargado."
      />

      <Ayuda pantalla="mediosPago" />
    </div>
  )
}
