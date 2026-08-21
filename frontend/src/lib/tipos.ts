/** Tipos que devuelve la API, compartidos por todas las pantallas. */

export type Rol = 'ADMIN' | 'ENCARGADO' | 'VENDEDOR'

export type TipoSucursal = 'LOCAL' | 'DEPOSITO'

export interface UsuarioActual {
  id: string
  nombre: string
  email: string
  rol: Rol
  sucursal_id: string | null
  sucursal_nombre: string | null
}

export interface Usuario {
  id: string
  nombre: string
  email: string
  rol: Rol
  sucursal_id: string | null
  activo: boolean
  ultimo_ingreso: string | null
}

export interface Sucursal {
  id: string
  nombre: string
  codigo: string
  tipo: TipoSucursal
  direccion: string | null
  localidad: string | null
  provincia: string | null
  telefono: string | null
  punto_venta_arca: number | null
  activa: boolean
}

export interface RespuestaIngreso {
  access_token: string
  token_type: string
  usuario: UsuarioActual
}

// ── Catálogo ──────────────────────────────────────────────────────────────────

export type Genero = 'HOMBRE' | 'MUJER' | 'UNISEX' | 'NINO' | 'NINA' | 'BEBE'

export type Temporada = 'VERANO' | 'INVIERNO' | 'ENTRETIEMPO' | 'ATEMPORAL'

export interface Marca {
  id: string
  nombre: string
  activa: boolean
}

export interface Talle {
  id: string
  valor: string
  orden: number
  activo: boolean
}

export interface CurvaTalle {
  id: string
  nombre: string
  activa: boolean
  talles: Talle[]
}

export interface Color {
  id: string
  nombre: string
  codigo_hex: string | null
  activo: boolean
}

export interface Categoria {
  id: string
  nombre: string
  curva_talle_id: string
  curva_nombre: string
  activa: boolean
}

export interface Variante {
  id: string
  producto_id: string
  talle_id: string
  talle: string
  color_id: string
  color: string
  codigo_hex: string | null
  sku: string
  codigo_barras: string | null
  activa: boolean
  /** Los importes llegan como texto para no perder los centavos. */
  precio_venta: string | null
  costo: string | null
}

export interface ImagenProducto {
  id: string
  orden: number
  url: string | null
}

export interface Producto {
  id: string
  nombre: string
  descripcion: string | null
  categoria_id: string
  categoria: string
  marca_id: string | null
  marca: string | null
  genero: Genero
  temporada: Temporada
  activo: boolean
  variantes: Variante[]
  imagenes: ImagenProducto[]
}

export interface ProductoEnLista {
  id: string
  nombre: string
  categoria: string
  marca: string | null
  genero: Genero
  temporada: Temporada
  activo: boolean
  cantidad_variantes: number
  precio_desde: string | null
  precio_hasta: string | null
  imagen_url: string | null
}

export interface Precio {
  id: string
  variante_id: string
  costo: string | null
  precio_venta: string
  precio_mayorista: string | null
  vigente_desde: string
  vigente_hasta: string | null
  motivo: string | null
}
