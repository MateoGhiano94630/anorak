/** Las rutas del sistema. */

import { Route, Routes } from 'react-router-dom'

import { Layout } from './componentes/Layout'
import { RutaProtegida } from './componentes/RutaProtegida'
import { Ingreso } from './paginas/Ingreso'
import { Inicio } from './paginas/Inicio'
import { Usuarios } from './paginas/Usuarios'

export function App() {
  return (
    <Routes>
      <Route path="/ingreso" element={<Ingreso />} />
      <Route element={<RutaProtegida />}>
        <Route element={<Layout />}>
          <Route index element={<Inicio />} />
          <Route element={<RutaProtegida roles={['ADMIN']} />}>
            <Route path="usuarios" element={<Usuarios />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  )
}
