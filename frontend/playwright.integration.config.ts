import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './integration',
  workers: 1,
  timeout: 60000,
  use: {
    baseURL: 'http://127.0.0.1:3101',
    channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: [
    {
      command: 'node scripts/integration-backend.mjs',
      url: 'http://127.0.0.1:18101/api/health',
      reuseExistingServer: false,
    },
    {
      command: 'node scripts/start-integration.mjs',
      url: 'http://127.0.0.1:3101',
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});
