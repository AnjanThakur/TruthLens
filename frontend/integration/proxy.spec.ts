import { test, expect } from '@playwright/test';

test('all five inputs pass through the real server proxy with mocks disabled', async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('Choose a synthetic example')).toHaveCount(0);
  expect((await (await request.get('/api/health')).json()).status).toBe(
    'offline-integration-fixture',
  );
  await page
    .getByLabel('Paste the message you want to check', { exact: true })
    .fill('A fictional test claim for integration.');
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await expect(page.getByText(/Partial check: some evidence/)).toBeVisible();
  await expect(page.getByText('Unconfirmed', { exact: true })).toBeVisible();
  for (const [button, name, mimeType, data] of [
    ['Screenshot', 'test.png', 'image/png', '\x89PNG\r\n\x1a\nfixture'],
    ['Voice note', 'test.ogg', 'audio/ogg', 'OggSfixture'],
    ['PDF', 'test.pdf', 'application/pdf', '%PDF-fixture'],
  ]) {
    await page.getByRole('button', { name: 'Start again', exact: true }).click();
    await page.getByRole('button', { name: button, exact: true }).click();
    await page
      .getByLabel('Choose a file', { exact: true })
      .setInputFiles({ name, mimeType, buffer: Buffer.from(data, 'latin1') });
    await page.getByRole('button', { name: 'Extract text', exact: true }).click();
    await expect(page.getByLabel('Extracted text', { exact: true })).toHaveValue(
      /fictional extracted claim/,
    );
    await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'What the evidence says' })).toBeVisible();
  }
  await page.getByRole('button', { name: 'Start again', exact: true }).click();
  await page.getByRole('button', { name: 'Article link', exact: true }).click();
  await page.getByLabel('Public article URL').fill('https://example.test/offline-article');
  await page.getByRole('button', { name: 'Extract text', exact: true }).click();
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await expect(page.getByRole('link', { name: /Offline source fixture/ })).toHaveAttribute(
    'href',
    'https://example.test/source',
  );
  for (const language of ['hi', 'mr', 'en']) {
    await page.locator('#language').selectOption(language);
    const translated = page.waitForResponse((response) => response.url().endsWith('/api/explain'));
    await page.locator('.explanation-tools button').click();
    expect((await translated).status()).toBe(200);
    await expect(page.getByText(/OFFLINE TRANSLATION FIXTURE/)).toBeVisible();
    await expect(page.getByRole('link', { name: /Offline source fixture/ })).toHaveAttribute(
      'href',
      'https://example.test/source',
    );
  }
  const calls = await (await request.get('http://127.0.0.1:18101/__test/calls')).json();
  for (const kind of ['text', 'image', 'audio', 'pdf', 'url'])
    expect(
      calls.some(
        (c: { path: string; kind?: string }) => c.path === '/api/verify' && c.kind === kind,
      ),
    ).toBe(true);
  expect(errors).toEqual([]);
});

test('upstream failure and actual proxy deadline show errors without canned verdicts', async ({
  page,
}) => {
  await page.goto('/');
  for (const marker of ['SIMULATE_UNAVAILABLE', 'SIMULATE_TIMEOUT']) {
    await page
      .getByLabel('Paste the message you want to check', { exact: true })
      .fill(`Fictional integration ${marker}`);
    await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
    const alert = page
      .getByRole('region', { name: 'Verify a forward', exact: true })
      .getByRole('alert');
    await expect(alert).toContainText(
      marker === 'SIMULATE_TIMEOUT' ? 'took too long' : 'service is unavailable',
    );
    await expect(page.getByRole('article')).toHaveCount(0);
  }
});

test('hosting upload cap is shown and enforced before extraction', async ({ page, request }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Screenshot', exact: true }).click();
  await expect(page.getByText('Up to 1 MB. Supported formats are listed below.')).toBeVisible();
  const before = await (await request.get('http://127.0.0.1:18101/__test/calls')).json();
  const oversized = Buffer.alloc(1048577);
  await page
    .getByLabel('Choose a file', { exact: true })
    .setInputFiles({ name: 'large.png', mimeType: 'image/png', buffer: oversized });
  await expect(
    page.getByRole('region', { name: 'Verify a forward', exact: true }).getByRole('alert'),
  ).toContainText('upload limit');
  const response = await request.post('/api/extract', {
    headers: { Origin: 'http://127.0.0.1:3101' },
    multipart: { file: { name: 'large.png', mimeType: 'image/png', buffer: oversized } },
  });
  expect(response.status()).toBe(413);
  const after = await (await request.get('http://127.0.0.1:18101/__test/calls')).json();
  expect(after).toEqual(before);
});
