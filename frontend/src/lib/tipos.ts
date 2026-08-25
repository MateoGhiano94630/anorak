/** Tipos que devuelve la API, compartidos por todas las pantallas. */

export type Rol = 'ADMIN' | 'ENCARGADO' | 'VENDEDOR'

export interface UsuarioActual {
  id: string
  nombre: string
  email: string
  rol: Rol
}

export interface Usuario {
  id: string
  nombre: string
  email: string
  rol: Rol
  activo: boolean
  ultimo_ingreso: string | null
}

export interface RespuestaIngreso {
  access_token: string
  token_type: string
  usuario: UsuarioActual
}

// ── Caja ──────────────────────────────────────────────────────────────────────

export type TipoMedioPago =
  'EFECTIVO' | 'TARJETA_DEBITO' | 'TARJETA_CREDITO' | 'QR' | 'TRANSFERENCIA'

export type EstadoSesionCaja = 'ABIERTA' | 'CERRADA'

export type TipoMovimientoCaja =
  | 'APERTURA'
  | 'COBRO'
  | 'INGRESO'
  | 'RETIRO'
  | 'GASTO'
  | 'DEVOLUCION'
  | 'DIFERENCIA'
  | 'CIERRE'

export type TipoDocumentoCaja = 'VENTA' | 'DEVOLUCION' | 'CAMBIO' | 'COMPRA'

/** Los tres que carga una persona a mano. */
export type TipoMovimientoManual = 'INGRESO' | 'RETIRO' | 'GASTO'

export interface MedioPago {
  id: string
  nombre: string
  tipo: TipoMedioPago
  afecta_efectivo: boolean
  /** Los importes llegan como texto para no perder los centavos. */
  comision_porcentaje: string | null
  dias_acreditacion: number | null
  orden: number
  activo: boolean
}

export interface MovimientoCaja {
  id: string
  numero: number
  tipo: TipoMovimientoCaja
  medio_pago_id: string
  medio_pago: string
  importe: string
  concepto: string | null
  comprobante: string | null
  documento_tipo: TipoDocumentoCaja | null
  documento_id: string | null
  fecha: string
  usuario_id: string | null
}

export interface TotalPorMedio {
  medio_pago_id: string
  medio_pago: string
  total: string
}

export interface SesionCaja {
  id: string
  estado: EstadoSesionCaja
  fecha_apertura: string
  abierta_por: string
  abierta_por_nombre: string | null
  monto_inicial: string
  fecha_cierre: string | null
  cerrada_por: string | null
  cerrada_por_nombre: string | null
  /** Nulos mientras la caja está abierta: el arqueo es a ciegas. */
  efectivo_declarado: string | null
  efectivo_esperado: string | null
  diferencia: string | null
  motivo_diferencia: string | null
  monto_retirado: string | null
  fondo_dejado: string | null
  observaciones: string | null
  totales_por_medio: TotalPorMedio[]
  movimientos: MovimientoCaja[]
}

export interface SesionEnLista {
  id: string
  estado: EstadoSesionCaja
  fecha_apertura: string
  abierta_por_nombre: string | null
  fecha_cierre: string | null
  cerrada_por_nombre: string | null
  monto_inicial: string
  efectivo_declarado: string | null
  efectivo_esperado: string | null
  diferencia: string | null
  monto_retirado: string | null
}

// ── Ventas ────────────────────────────────────────────────────────────────────

export type EstadoVenta = 'REGISTRADA' | 'ANULADA'

export interface Articulo {
  id: string
  nombre: string
  categoria: string | null
  /** Los importes llegan como texto para no perder los centavos. */
  precio: string
  activo: boolean
}

export interface LineaVenta {
  id: string
  numero: number
  articulo_id: string | null
  descripcion: string
  talle: string | null
  cantidad: number
  precio_unitario: string
  descuento: string
  subtotal: string
}

export interface CobroVenta {
  medio_pago_id: string
  medio_pago: string
  importe: string
  /** True cuando es la reversión de una anulación. */
  es_reversion: boolean
}

export interface Venta {
  id: string
  numero: number
  estado: EstadoVenta
  fecha: string
  registrada_por: string
  registrada_por_nombre: string | null
  sesion_caja_id: string
  subtotal: string
  descuento: string
  total: string
  observaciones: string | null
  anulada_por_nombre: string | null
  fecha_anulacion: string | null
  motivo_anulacion: string | null
  lineas: LineaVenta[]
  cobros: CobroVenta[]
}

export interface VentaEnLista {
  id: string
  numero: number
  estado: EstadoVenta
  fecha: string
  registrada_por_nombre: string | null
  cantidad_articulos: number
  total: string
}

/** Una línea del carrito, antes de que la venta exista. */
export interface LineaDelCarrito {
  /** Clave local para dibujar la lista. La venta todavía no tiene id. */
  clave: string
  articulo_id: string | null
  descripcion: string
  talle: string
  cantidad: number
  precio_unitario: string
  descuento: string
}
