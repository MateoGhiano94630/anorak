/** Las rutas del sistema. */

import { Route, Routes } from 'react-router-dom'

import { Layout } from './componentes/Layout'
import { RutaProtegida } from './componentes/RutaProtegida'
import { Inicio } from './paginas/Inicio'
import { Ingreso } from './paginas/Ingreso'
import { Sucursales } from './paginas/Sucursales'
import { Usuarios } from './paginas/Usuarios'

export function App() {
  return (
    <Routes>
      <Route path="/ingreso" element={<Ingreso />} />
      <Route element={<RutaProtegida />}>
        <Route element={<Layout />}>
          <Route index element={<Inicio />} />
          <Route element={<RutaProtegida roles={['ADMIN']} />}>
            <Route path="sucursales" element={<Sucursales />} />
            <Route path="usuarios" element={<Usuarios />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  )
}
