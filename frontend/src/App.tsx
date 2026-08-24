/** Las rutas del sistema. */

import { Route, Routes } from 'react-router-dom'

import { Layout } from './componentes/Layout'
import { RutaProtegida } from './componentes/RutaProtegida'
import { Caja } from './paginas/Caja'
import { CierresCaja } from './paginas/CierresCaja'
import { Ingreso } from './paginas/Ingreso'
import { Inicio } from './paginas/Inicio'
import { MediosPago } from './paginas/MediosPago'
import { Usuarios } from './paginas/Usuarios'

export function App() {
  return (
    <Routes>
      <Route path="/ingreso" element={<Ingreso />} />
      <Route element={<RutaProtegida />}>
        <Route element={<Layout />}>
          <Route index element={<Inicio />} />
          {/* La caja la abre y la cierra quien atiende, así que entra
              cualquiera. El historial de cierres no: lo revisa el encargado. */}
          <Route path="caja" element={<Caja />} />
          <Route element={<RutaProtegida roles={['ENCARGADO']} />}>
            <Route path="caja/cierres" element={<CierresCaja />} />
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
