/**
 * El marco de todas las pantallas: menú, quién entró y botón de salida.
 *
 * El menú se arma de una sola lista y cada opción declara qué puestos la ven.
 * En pantalla ancha va como columna a la izquierda; en el celular, como una
 * fila que se desliza arriba del contenido.
 */

import { NavLink, Outlet } from 'react-router-dom'

import { useSesion } from '../contexto/sesion'
import type { Rol } from '../lib/tipos'
import { Boton } from './Boton'

interface OpcionMenu {
  ruta: string
  texto: string
  /** Puestos que ven la opción. El administrador ve todas siempre. */
  roles: Rol[]
}

const MENU: OpcionMenu[] = [
  { ruta: '/', texto: 'Inicio', roles: ['ADMIN', 'ENCARGADO', 'VENDEDOR'] },
  { ruta: '/catalogo', texto: 'Catálogo', roles: ['ADMIN', 'ENCARGADO', 'VENDEDOR'] },
  {
    ruta: '/existencias',
    texto: 'Existencias',
    roles: ['ADMIN', 'ENCARGADO', 'VENDEDOR'],
  },
  { ruta: '/movimientos', texto: 'Movimientos', roles: ['ADMIN', 'ENCARGADO'] },
  { ruta: '/catalogos', texto: 'Marcas y talles', roles: ['ADMIN', 'ENCARGADO'] },
  { ruta: '/sucursales', texto: 'Sucursales', roles: ['ADMIN'] },
  { ruta: '/usuarios', texto: 'Usuarios', roles: ['ADMIN'] },
]

export function Layout() {
  const { usuario, salir } = useSesion()
  if (usuario === null) return null

  const opciones = MENU.filter(
    (opcion) => usuario.rol === 'ADMIN' || opcion.roles.includes(usuario.rol),
  )

  const clasesOpcion = ({ isActive }: { isActive: boolean }): string =>
    `flex min-h-11 items-center whitespace-nowrap rounded-lg px-3 text-base ${
      isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
    }`

  return (
    <div className="min-h-dvh bg-slate-50 text-slate-900">
      <header className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3">
        <div>
          <p className="text-lg font-semibold">Anorak</p>
          <p className="text-xs text-slate-500">
            {usuario.nombre}
            {usuario.sucursal_nombre !== null ? ` · ${usuario.sucursal_nombre}` : ''}
          </p>
        </div>
        <Boton variante="secundario" onClick={salir}>
          Salir
        </Boton>
      </header>

      <div className="md:flex">
        <nav
          aria-label="Secciones"
          className="flex gap-2 overflow-x-auto border-b border-slate-200 bg-white p-2 md:w-56 md:shrink-0 md:flex-col md:border-r md:border-b-0 md:p-3"
        >
          {opciones.map((opcion) => (
            <NavLink key={opcion.ruta} to={opcion.ruta} end className={clasesOpcion}>
              {opcion.texto}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
