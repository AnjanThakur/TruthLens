import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
test('alert review stays honest and accessible when private integration is not configured', async ({
  page,
  request,
}) => {
  await page.goto('/alerts');
  await expect(page.getByRole('heading', { name: 'Alert review', exact: true })).toBeVisible();
  await expect(
    page.getByText('Alert integration is not configured.', { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve reviewed candidate' })).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations,
  ).toEqual([]);
  const result = await request.post('/api/alerts/contribute', {
    headers: { Origin: `http://localhost:${process.env.PLAYWRIGHT_PORT || '3000'}` },
    data: { consent: true },
  });
  expect(result.ok()).toBe(false);
  expect((await result.json()).accepted).toBeUndefined();
});
