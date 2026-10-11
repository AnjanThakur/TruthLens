import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: {
    baseURL: 'http://localhost:3000',
    channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' },
    },
    {
      name: 'mobile',
      use: {
        ...devices['Pixel 7'],
        defaultBrowserType: 'chromium',
        channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge',
      },
    },
  ],
  webServer: {
    command: 'npm run dev:mock -- --hostname 127.0.0.1',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
