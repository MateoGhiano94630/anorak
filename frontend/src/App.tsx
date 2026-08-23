/** Las rutas del sistema. */

import { Route, Routes } from 'react-router-dom'

import { Layout } from './componentes/Layout'
import { RutaProtegida } from './componentes/RutaProtegida'
import { Catalogo } from './paginas/Catalogo'
import { CatalogosBase } from './paginas/CatalogosBase'
import { Existencias } from './paginas/Existencias'
import { Inicio } from './paginas/Inicio'
import { Ingreso } from './paginas/Ingreso'
import { Movimientos } from './paginas/Movimientos'
import { ProductoDetalle } from './paginas/ProductoDetalle'
import { Sucursales } from './paginas/Sucursales'
import { Usuarios } from './paginas/Usuarios'

export function App() {
  return (
    <Routes>
      <Route path="/ingreso" element={<Ingreso />} />
      <Route element={<RutaProtegida />}>
        <Route element={<Layout />}>
          <Route index element={<Inicio />} />
          {/* El catálogo lo consulta cualquiera: el mostrador necesita ver
              precios y talles. Quién puede cargar y cambiar lo controla la
              API, no la ruta. */}
          <Route path="catalogo" element={<Catalogo />} />
          <Route path="catalogo/:productoId" element={<ProductoDetalle />} />
          {/* Las existencias también las consulta el mostrador: "¿la tenés en
              M?" es la pregunta más frecuente del local. Cargar y corregir lo
              controla la API. */}
          <Route path="existencias" element={<Existencias />} />
          <Route path="movimientos" element={<Movimientos />} />
          <Route element={<RutaProtegida roles={['ENCARGADO']} />}>
            <Route path="catalogos" element={<CatalogosBase />} />
          </Route>
          <Route element={<RutaProtegida roles={['ADMIN']} />}>
            <Route path="sucursales" element={<Sucursales />} />
            <Route path="usuarios" element={<Usuarios />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  )
}
