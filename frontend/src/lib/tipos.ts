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
