import { defineConfig, globalIgnores } from 'eslint/config';
import tseslint from 'typescript-eslint';
import hooks from 'eslint-plugin-react-hooks';
import a11y from 'eslint-plugin-jsx-a11y';
export default defineConfig([
  ...tseslint.configs.recommended,
  hooks.configs.flat.recommended,
  {
    ...a11y.flatConfigs.recommended,
    files: ['**/*.{tsx,jsx}'],
    settings: { 'jsx-a11y': { components: { Link: 'a' } } },
  },
  globalIgnores(['.next/**', 'next-env.d.ts', 'playwright-report/**', 'test-results/**']),
]);
