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
