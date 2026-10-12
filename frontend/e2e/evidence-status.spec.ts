import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import type { Verification } from '../src/lib/api/contracts';

test('fetched, failed, snippet, irrelevant and incomplete evidence remain distinct', async ({
  page,
}) => {
  const report = JSON.parse(
    readFileSync(new URL('../tests/fixtures/person1-response.json', import.meta.url), 'utf8'),
  ) as Verification;
  report.verification_id = 'mock-evidence-status';
  const claim = report.claims[0];
  const base = claim.evidence[0];
  report.claims = [claim];
  report.warnings = [
    'source_page_unavailable:url_fetch_error',
    'source_page_required_unavailable:url_fetch_error',
    'source_page_unavailable:url_no_text',
  ];
  claim.evidence = [
    {
      ...base,
      evidence_id: 'complete',
      url: 'https://publisher.example/complete',
      source_type: 'secondary',
      excerpt_provenance: 'fetched_page',
      authority_basis: 'Reviewed registry',
      directly_relevant: true,
      stance: 'supports',
      what_source_says: 'Exact fixture passage.',
    },
    {
      ...base,
      evidence_id: 'failed',
      url: 'https://publisher.example/failed',
      excerpt_provenance: 'search_excerpt',
      what_source_says: '',
      authority_basis:
        'source_fetch_failure=url_fetch_error; source_fetch_category=access_denied; source_fetch_http_status=403',
    },
    {
      ...base,
      evidence_id: 'snippet',
      url: 'https://publisher.example/snippet',
      excerpt_provenance: 'search_excerpt',
      authority_basis: '',
      what_source_says: '',
    },
    {
      ...base,
      evidence_id: 'namesake',
      url: 'https://publisher.example/namesake',
      excerpt_provenance: 'fetched_page',
      authority_basis: 'entity_mismatch: named subject missing',
      what_source_says: '',
    },
    {
      ...base,
      evidence_id: 'incomplete',
      url: 'https://publisher.example/incomplete',
      excerpt_provenance: 'fetched_page',
      authority_basis: 'incomplete_content: short video shell',
      what_source_says: '',
    },
  ];
  await page.route('**/api/verify', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(report),
    }),
  );
  await page.goto('/');
  await page.getByRole('button', { name: 'Use this example', exact: true }).click();
  await page.getByRole('button', { name: 'Check the facts', exact: true }).click();
  await page.getByText(/Full retrieved evidence ledger/).click();
  await expect(page.getByText('Complete reviewed page; excerpt assessed.')).toBeVisible();
  await expect(page.getByText('Page retrieval failed; snippet is not proof.')).toBeVisible();
  await expect(page.getByText('Publisher denied access · HTTP 403')).toBeVisible();
  await expect(page.getByText('Snippet only; not decisive evidence.')).toBeVisible();
  await expect(page.getByText('Not relevant to the exact named subject or claim.')).toBeVisible();
  await expect(page.getByText('Incomplete page; not decisive evidence.')).toBeVisible();
  await expect(page.locator('.service-notes > summary')).toHaveText('Notes from the service (1)');
  await page.locator('.service-notes > summary').click();
  await expect(
    page.getByText(
      'A source page was unavailable or incomplete. Only retrieved content could be assessed.',
    ),
  ).toHaveCount(1);
});
