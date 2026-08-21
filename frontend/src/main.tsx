import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { App } from './App'
import { ProveedorSesion } from './contexto/ProveedorSesion'
import './index.css'

const clienteConsultas = new QueryClient({
  defaultOptions: {
    queries: {
      // Un reintento y nada más: si el local se quedó sin internet, insistir
      // cinco veces solo demora el aviso de que no hay conexión.
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

const contenedor = document.getElementById('root')
if (contenedor === null) throw new Error('No se encontró el contenedor de la aplicación')

createRoot(contenedor).render(
  <StrictMode>
    <QueryClientProvider client={clienteConsultas}>
      <BrowserRouter>
        <ProveedorSesion>
          <App />
        </ProveedorSesion>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
