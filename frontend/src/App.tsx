/** Las rutas del sistema. */

import { Route, Routes } from 'react-router-dom'

import { Layout } from './componentes/Layout'
import { RutaProtegida } from './componentes/RutaProtegida'
import { Articulos } from './paginas/Articulos'
import { Caja } from './paginas/Caja'
import { CierresCaja } from './paginas/CierresCaja'
import { Ingreso } from './paginas/Ingreso'
import { Inicio } from './paginas/Inicio'
import { MediosPago } from './paginas/MediosPago'
import { Usuarios } from './paginas/Usuarios'
import { Vender } from './paginas/Vender'
import { Ventas } from './paginas/Ventas'

export function App() {
  return (
    <Routes>
      <Route path="/ingreso" element={<Ingreso />} />
      <Route element={<RutaProtegida />}>
        <Route element={<Layout />}>
          <Route index element={<Inicio />} />
          {/* La caja la abre y la cierra quien atiende, así que entra
              cualquiera. El historial de cierres no: lo revisa el encargado. */}
          {/* Vender y consultar ventas son del mostrador. Anular tambien:
              es lo que arregla un error con el cliente enfrente. */}
          <Route path="vender" element={<Vender />} />
          <Route path="ventas" element={<Ventas />} />
          <Route path="caja" element={<Caja />} />
          <Route element={<RutaProtegida roles={['ENCARGADO']} />}>
            <Route path="caja/cierres" element={<CierresCaja />} />
            <Route path="articulos" element={<Articulos />} />
          </Route>
          <Route element={<RutaProtegida roles={['ADMIN']} />}>
            <Route path="medios-pago" element={<MediosPago />} />
            <Route path="usuarios" element={<Usuarios />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  )
}
