import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
await mkdir('../docs/qa', { recursive: true });
const browser = await chromium.launch({
  channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge',
  headless: true,
});
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  page.on('pageerror', (error) => console.log('BROWSER ERROR:', error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') console.log('CONSOLE ERROR:', message.text());
  });
  await page.goto('http://localhost:3000');
  await page.getByRole('button', { name: 'Use this example' }).waitFor();
  await page.waitForFunction(() => document.documentElement.dataset.reading === 'standard');
  await page.screenshot({ path: '../docs/qa/desktop-home.png', fullPage: true });
  await page.getByRole('button', { name: 'Use this example' }).click();
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await page.getByRole('heading', { name: 'What the evidence says' }).waitFor();
  await page.screenshot({ path: '../docs/qa/desktop-results.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '../docs/qa/mobile-results.png', fullPage: true });
  await page.locator('#language').selectOption('mr');
  await page.getByRole('button', { name: 'सोपे वाचन', exact: true }).click();
  await page.screenshot({ path: '../docs/qa/marathi-easy.png', fullPage: true });
  console.log(resolve('../docs/qa'));
} finally {
  await browser.close();
}
