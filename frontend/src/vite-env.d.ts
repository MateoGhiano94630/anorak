/// <reference types="vite/client" />

/**
 * Las variables de entorno que usa el frontend, declaradas para que
 * TypeScript no las trate como `any`. Si se agrega una nueva, va acá.
 */
interface ImportMetaEnv {
  /** Dirección de la API. Si no está, se usa /api (el proxy de desarrollo). */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
