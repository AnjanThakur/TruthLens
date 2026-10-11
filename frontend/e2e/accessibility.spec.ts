import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
test('home, evidence results and translated easy mode meet automated WCAG checks', async ({
  page,
}) => {
  await page.goto('/');
  await page.waitForFunction(() => document.documentElement.dataset.reading === 'standard');
  let result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(result.violations).toEqual([]);
  await page.getByRole('button', { name: 'Use this example' }).click();
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await page.getByRole('heading', { name: 'What the evidence says' }).waitFor();
  result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(result.violations).toEqual([]);
  await page.locator('#language').selectOption('mr');
  await page.getByRole('button', { name: 'सोपे वाचन', exact: true }).click();
  result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(result.violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
