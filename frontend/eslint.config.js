import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'dev-dist', 'playwright-report', 'coverage'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.strictTypeChecked],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // allowConstantExport: los archivos de componentes exportan también
      // alguna constante de estilo compartida, y eso no rompe el refresco.
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // `any` está prohibido en el proyecto: que sea error y no aviso.
      '@typescript-eslint/no-explicit-any': 'error',
      // `onChange={(e) => setNombre(e.target.value)}` es la forma normal de
      // escribir un manejador en React. La regla, sin esta opción, obliga a
      // ponerle llaves a todos y no evita ningún error real.
      '@typescript-eslint/no-confusing-void-expression': [
        'error',
        { ignoreArrowShorthand: true },
      ],
      // Interpolar un número en un texto (`${anio}-${mes}`) es exactamente lo
      // que hace falta para armar una fecha. Lo que no se permite es meter
      // objetos o valores que puedan ser nulos.
      '@typescript-eslint/restrict-template-expressions': [
        'error',
        { allowNumber: true },
      ],
    },
  },
  prettier,
)
