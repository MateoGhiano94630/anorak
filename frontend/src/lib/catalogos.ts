/**
 * Las listas del catálogo que varias pantallas necesitan a la vez.
 *
 * Están juntas para que TanStack Query las comparta: entrar a una prenda y
 * volver al listado no vuelve a pedir las marcas ni los colores, que casi
 * nunca cambian.
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query'

import { pedir } from './api'
import type { Categoria, Color, CurvaTalle, Marca, Sucursal } from './tipos'

export function useMarcas(): UseQueryResult<Marca[]> {
  return useQuery({ queryKey: ['marcas'], queryFn: () => pedir<Marca[]>('/marcas') })
}

export function useColores(): UseQueryResult<Color[]> {
  return useQuery({ queryKey: ['colores'], queryFn: () => pedir<Color[]>('/colores') })
}

export function useCategorias(): UseQueryResult<Categoria[]> {
  return useQuery({
    queryKey: ['categorias'],
    queryFn: () => pedir<Categoria[]>('/categorias'),
  })
}

export function useCurvas(): UseQueryResult<CurvaTalle[]> {
  return useQuery({
    queryKey: ['curvas-talle'],
    queryFn: () => pedir<CurvaTalle[]>('/curvas-talle'),
  })
}

export function useSucursales(): UseQueryResult<Sucursal[]> {
  return useQuery({
    queryKey: ['sucursales'],
    queryFn: () => pedir<Sucursal[]>('/sucursales'),
  })
}
