import { expect, test } from '@playwright/test'

test.describe('Ingreso', () => {
  test('sin sesión, cualquier pantalla lleva al ingreso', async ({ page }) => {
    await page.goto('/usuarios')
    await expect(page.getByRole('button', { name: 'Entrar' })).toBeVisible()
  })

  test('la ayuda del ingreso se abre y explica por qué hay que volver a entrar', async ({
    page,
  }) => {
    await page.goto('/ingreso')
    await page.getByRole('button', { name: '¿Cómo se usa esta pantalla?' }).click()
    await expect(
      page.getByText('¿Por qué me pide entrar de nuevo si recargo la página?'),
    ).toBeVisible()
  })

  test('los campos de carga no bajan de 16px', async ({ page }) => {
    // Por debajo de 16px, iPhone amplía la pantalla solo al tocar el campo.
    await page.goto('/ingreso')
    const tamanio = await page
      .getByLabel('Correo')
      .evaluate((elemento) => window.getComputedStyle(elemento).fontSize)
    expect(Number.parseFloat(tamanio)).toBeGreaterThanOrEqual(16)
  })
})
