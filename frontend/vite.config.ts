import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
// defineConfig sale de vitest y no de vite: es el mismo, con la clave `test`
// tipada. Con el de vite, la configuración de los tests no compila.
import { defineConfig } from 'vitest/config'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Anorak — gestión del local',
        short_name: 'Anorak',
        description: 'Catálogo, stock y punto de venta del local',
        lang: 'es-AR',
        start_url: '/',
        display: 'standalone',
        background_color: '#0f172a',
        theme_color: '#0f172a',
      },
      workbox: {
        // La API nunca se cachea acá: lo que tiene que funcionar sin conexión
        // es el punto de venta, y eso se resuelve con la cola en IndexedDB
        // (Dexie), no guardando respuestas viejas del servidor. Una respuesta
        // de stock cacheada es peor que no tener respuesta.
        navigateFallbackDenylist: [/^\/api/],
      },
    }),
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (ruta) => ruta.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    // Solo lo de src: los archivos de e2e/ los corre Playwright, y si Vitest
    // los levanta falla con un error que no dice nada sobre el problema real.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/setupTests.ts'],
  },
})
