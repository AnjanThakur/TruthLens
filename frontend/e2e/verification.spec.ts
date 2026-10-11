import { test, expect } from '@playwright/test';
import backendResult from '../tests/fixtures/person1-response.json' with { type: 'json' };
import type { Verification } from '../src/lib/api/contracts';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test('actual backend shape renders partial warnings and structured context', async ({ page }) => {
  const report = structuredClone(backendResult) as Verification;
  report.status = 'partial';
  report.warnings = ['search_unavailable: one dependency failed'];
  report.claims[0].temporal_context.notes = 'The event date is not established.';
  await page.route('**/api/verify', (route) => route.fulfill({ json: report }));
  await page
    .getByLabel('Paste the message you want to check', { exact: true })
    .fill('A fictional test claim.');
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await expect(page.getByText(/Partial check: some evidence/)).toBeVisible();
  await expect(
    page.getByText('The event date is not established.', { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole('link', { name: /Offline source fixture/ })).toHaveAttribute(
    'href',
    'https://example.test/source',
  );
});

test('long PDF preview requires selecting a page chunk before verification', async ({ page }) => {
  await page.route('**/api/extract', (route) =>
    route.fulfill({
      json: {
        text: 'Preview only',
        detected_language: 'en',
        input_type: 'pdf',
        warnings: ['extraction_text_truncated'],
        extraction_details: {
          text_is_preview: true,
          chunks: [{ chunk_id: 1, page_number: 2, text: 'Actual returned page chunk.' }],
        },
      },
    }),
  );
  await page.getByRole('button', { name: 'PDF', exact: true }).click();
  await page.getByLabel('Choose a file', { exact: true }).setInputFiles({
    name: 'test.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-fixture'),
  });
  await page.getByRole('button', { name: 'Extract text', exact: true }).click();
  await expect(page.getByLabel('Extracted text', { exact: true })).toHaveValue('');
  await page.locator('#page-chunk').selectOption('0');
  await expect(page.getByLabel('Extracted text', { exact: true })).toHaveValue(
    'Actual returned page chunk.',
  );
  await expect(page.getByText(/Each result covers only the selected text/)).toBeVisible();
});
test('multi-claim forward, separate evidence, no implicit persistence', async ({ page }) => {
  await expect(
    page.getByText('SYNTHETIC DEMO · Fictional examples, not real fact-checks', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Use this example' }).click();
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'What the evidence says' })).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(2);
  await expect(page.getByText('Verified', { exact: true })).toBeVisible();
  await expect(page.getByText('False', { exact: true })).toBeVisible();
  await expect(page.getByText('Synthetic reports cannot be saved to live history.')).toBeVisible();
  await expect(page.getByRole('link', { name: /Synthetic test notice eligible/ })).toHaveAttribute(
    'href',
    'https://example.org/truthlens-fixture/eligible',
  );
});
test('every non-text sample passes extraction review and verification', async ({ page }) => {
  for (const value of ['1', '2', '3', '4']) {
    await page.locator('#fixture').selectOption(value);
    await page.getByRole('button', { name: 'Use this example' }).click();
    await expect(page.getByLabel('Extracted text', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'What the evidence says' })).toBeVisible();
    await page.getByRole('button', { name: 'Start again', exact: true }).click();
  }
});
test('actual upload and URL controls request simulated extraction explicitly', async ({ page }) => {
  await page.getByRole('button', { name: 'Screenshot', exact: true }).click();
  await page.getByLabel('Choose a file', { exact: true }).setInputFiles({
    name: 'sample.png',
    mimeType: 'image/png',
    buffer: Buffer.from('synthetic-upload-not-real-ocr'),
  });
  await page.getByRole('button', { name: 'Extract text', exact: true }).click();
  await expect(page.getByLabel('Extracted text', { exact: true })).toHaveValue(
    'Office hours are 10 AM to 4 PM.',
  );
  await page.getByRole('button', { name: 'Article link', exact: true }).click();
  await page.getByLabel('Public article URL').fill('https://example.org/test');
  await page.getByRole('button', { name: 'Extract text', exact: true }).click();
  await expect(page.getByText('Mock article, not fetched from the public web')).toBeVisible();
});
test('edited extraction is preserved and cannot be assigned an unrelated canned verdict', async ({
  page,
}) => {
  await page.locator('#fixture').selectOption('1');
  await page.getByRole('button', { name: 'Use this example' }).click();
  await page
    .getByLabel('Extracted text', { exact: true })
    .fill('A corrected message with different office hours.');
  await expect(page.getByText(/You edited the extracted text/)).toBeVisible();
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await expect(
    page.getByRole('region', { name: 'Verify a forward', exact: true }).getByRole('alert'),
  ).toContainText('Synthetic mode only demonstrates');
  await expect(page.getByLabel('Extracted text', { exact: true })).toHaveValue(
    'A corrected message with different office hours.',
  );
  await expect(page.getByRole('article')).toHaveCount(0);
});
test('unconfirmed stays neutral; language and easy reading preserve source identity', async ({
  page,
}) => {
  await page.locator('#fixture').selectOption('5');
  await page.getByRole('button', { name: 'Use this example' }).click();
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await expect(page.getByText('Unconfirmed', { exact: true })).toBeVisible();
  await expect(page.getByText('False', { exact: true })).toHaveCount(0);
  await page.locator('#language').selectOption('hi');
  await expect(page.locator('html')).toHaveAttribute('lang', 'hi');
  await expect(page.getByText('पुष्टि नहीं हुई', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'आसान पठन', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('data-reading', 'easy');
  await page.getByRole('button', { name: 'व्याख्या बदलें', exact: true }).click();
  await expect(page.getByText(/अनुवादित व्याख्या उपलब्ध नहीं है/)).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'An unspecified event will occur tomorrow.' }),
  ).toBeVisible();
});
test('offline errors never fall back to fixtures; keyboard and mobile remain usable', async ({
  page,
}) => {
  await page.getByRole('button', { name: 'Use this example' }).click();
  await page.route('**/api/verify', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'BACKEND_OFFLINE' } }),
    }),
  );
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await expect(
    page.getByRole('region', { name: 'Verify a forward', exact: true }).getByRole('alert'),
  ).toContainText('verification service is unavailable');
  await expect(page.getByRole('article')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
});
test('private history fails safely without credentials', async ({ page }) => {
  await page.getByRole('link', { name: 'Private history', exact: true }).first().click();
  await expect(
    page.getByText(
      'Private history is not connected yet. Verification is available without an account.',
    ),
  ).toBeVisible();
  const response = await page.request.get('/api/history');
  expect(response.status()).toBe(503);
});

test('rapid submissions are deduplicated and cancelled responses never replace the input', async ({
  page,
}) => {
  await page.getByRole('button', { name: 'Use this example' }).click();
  let requests = 0;
  let release!: () => void;
  let finish!: () => void;
  const blocked = new Promise<void>((resolve) => {
    release = resolve;
  });
  const handled = new Promise<void>((resolve) => {
    finish = resolve;
  });
  await page.route('**/api/verify', async (route) => {
    requests += 1;
    await blocked;
    try {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'BACKEND_OFFLINE' } }),
      });
    } catch {
      /* Expected when the client aborts the request. */
    } finally {
      finish();
    }
  });
  await page.getByRole('button', { name: 'Check the facts', exact: true }).evaluate((button) => {
    if (button instanceof HTMLButtonElement) {
      button.click();
      button.click();
    }
  });
  await expect.poll(() => requests).toBe(1);
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  release();
  await handled;
  await expect(page.getByRole('button', { name: 'Check the facts', exact: true })).toBeEnabled();
  await expect(page.getByLabel('Paste the message you want to check')).toHaveValue(/Scheme X/);
  await expect(page.getByRole('article')).toHaveCount(0);
  expect(requests).toBe(1);
});
