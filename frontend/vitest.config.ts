import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      'server-only': fileURLToPath(new URL('./tests/server-only.ts', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    fileParallelism: false,
    setupFiles: ['./tests/setup.ts'],
    exclude: ['node_modules/**', '.next/**', 'e2e/**', 'integration/**'],
  },
});
