import assert from 'node:assert/strict';
import { chromium } from '@playwright/test';
const origin = process.env.SMOKE_ORIGIN || 'http://localhost:3001';
const home = await fetch(origin);
assert.equal(home.status, 200);
const policy = home.headers.get('content-security-policy');
assert.ok(policy.includes("'nonce-"));
assert.ok(!policy.includes('unsafe-eval'));
assert.equal(home.headers.get('x-content-type-options'), 'nosniff');
const html = await home.text();
assert.ok(!html.includes('Choose a synthetic example'));
const health = await fetch(`${origin}/api/health`);
assert.equal(health.status, 503);
const verification = await fetch(`${origin}/api/verify`, {
  method: 'POST',
  headers: { Origin: origin, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: 'A new arbitrary claim for the production outage test.',
    input_type: 'text',
  }),
});
assert.equal(verification.status, 503);
assert.ok(!(await verification.json()).claims);
const browser = await chromium.launch({
  channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge',
  headless: true,
});
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error' && /hydration|hydrated|Refused to/.test(message.text()))
      errors.push(message.text());
  });
  await page.goto(origin);
  await page.waitForFunction(() => document.documentElement.dataset.reading === 'standard');
  await page
    .getByLabel('Paste the message you want to check')
    .fill('A new arbitrary claim for the production outage test.');
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await page
    .getByRole('region', { name: 'Verify a forward', exact: true })
    .getByRole('alert')
    .filter({ hasText: 'has not been connected' })
    .waitFor();
  assert.equal(await page.getByRole('article').count(), 0);
  assert.deepEqual(errors, []);
  console.log(
    'Production smoke passed: CSP nonce, no eval, anonymous UI, no fixture fallback, honest unavailable service, no hydration/runtime errors.',
  );
} finally {
  await browser.close();
}
