import React from 'react';
import { expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Results } from '@/components/results';
import { PreferencesProvider } from '@/components/preferences';
import {
  displayWarnings,
  evidenceState,
  evidenceStateText,
  relevantSources,
  retrievalDiagnostic,
  warningText,
} from '@/lib/results';
import { fixtures } from '@/lib/fixtures';
it('shows failed assessment distinctly and copies fetched excerpts even without model notes', async () => {
  const report = structuredClone(fixtures[0].verification);
  report.status = 'partial';
  report.warnings = ['llm_timeout'];
  report.claims = [report.claims[0]];
  const claim = report.claims[0];
  claim.verdict = 'unconfirmed';
  claim.limitations = ['Evidence assessment failed; no definitive verdict was accepted.'];
  claim.evidence = [
    {
      ...claim.evidence[0],
      source_type: 'secondary',
      excerpt_provenance: 'fetched_page',
      authority_basis: 'Reviewed fixture',
      what_source_says: '',
      directly_relevant: false,
      stance: 'unclear',
      excerpt: 'An actual fetched fictional body, not a generated assessment.',
    },
  ];
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  render(
    <PreferencesProvider>
      <Results result={report} />
    </PreferencesProvider>,
  );
  expect(
    screen.getAllByText(/Evidence was retrieved, but AI assessment failed/).length,
  ).toBeGreaterThan(0);
  expect(screen.queryByText(/awaiting evidence assessment/)).not.toBeInTheDocument();
  expect(screen.getByText(/AI evidence assessment timed out/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /copy/i }));
  await waitFor(() => expect(writeText).toHaveBeenCalled());
  const copied = writeText.mock.calls[0][0];
  expect(copied).toContain(claim.evidence[0].excerpt);
  expect(copied).toContain('AI assessment failed');
  expect(copied).not.toContain('llm_timeout');
});
it('selects up to three directly assessed fetched sources, retaining neutral entries only in the ledger', () => {
  const claim = structuredClone(fixtures[0].verification.claims[0]);
  const source = claim.evidence[0];
  claim.evidence = Array.from({ length: 5 }, (_, i) => ({
    ...source,
    evidence_id: String(i),
    directly_relevant: true,
    source_type: 'primary',
    excerpt_provenance: 'fetched_page',
    stance: 'supports',
  }));
  claim.evidence.unshift({
    ...source,
    evidence_id: 'neutral',
    stance: 'neutral',
    directly_relevant: false,
  });
  expect(relevantSources(claim)).toHaveLength(3);
  expect(relevantSources(claim).some((s) => s.stance === 'neutral')).toBe(false);
});
it('renders invalid dates safely and explains partial processing without leaking technical codes', () => {
  const report = structuredClone(fixtures[0].verification);
  report.status = 'partial';
  report.warnings = ['llm_provider_error'];
  report.claims[0].evidence[0].published_at = 'not a date';
  render(
    <PreferencesProvider>
      <Results result={report} />
    </PreferencesProvider>,
  );
  expect(screen.queryByText('llm_provider_error')).not.toBeInTheDocument();
  expect(screen.getByText(/AI processing was unavailable/)).toBeInTheDocument();
  expect(screen.getAllByText('Date not provided').length).toBeGreaterThan(0);
  expect(warningText('source_page_unavailable:url_no_text', 'hi')).not.toContain('url_no_text');
});
it('labels unavailable search excerpts and excludes them from concise verdict sources', () => {
  const report = structuredClone(fixtures[0].verification);
  const claim = report.claims[0];
  claim.evidence[0].excerpt_provenance = 'search_excerpt';
  claim.evidence[0].source_type = 'other';
  claim.evidence[0].stance = 'supports';
  claim.evidence[0].directly_relevant = true;
  claim.evidence[0].title = 'Unavailable publisher fixture';
  report.claims = [claim];
  render(
    <PreferencesProvider>
      <Results result={report} />
    </PreferencesProvider>,
  );
  const ledger = screen.getByText(/Full retrieved evidence ledger/).closest('details')!;
  expect(within(ledger).getByText(/Search excerpt only/)).toBeVisible();
  expect(
    relevantSources(claim).some((source) => source.excerpt_provenance === 'search_excerpt'),
  ).toBe(false);
});

it('distinguishes retrieval failures, snippets, incomplete, irrelevant and assessed pages', () => {
  const base = structuredClone(fixtures[0].verification.claims[0].evidence[0]);
  const complete = {
    ...base,
    source_type: 'secondary',
    excerpt_provenance: 'fetched_page' as const,
    authority_basis: 'Reviewed registry',
    directly_relevant: true,
    what_source_says: 'Exact quotation',
  };
  expect(evidenceState(complete)).toBe('assessed');
  expect(evidenceState({ ...complete, what_source_says: '' })).toBe('unassessed');
  expect(evidenceState({ ...complete, source_type: 'other' })).toBe('unreviewed');
  expect(evidenceState({ ...complete, authority_basis: 'entity_mismatch: subject missing' })).toBe(
    'irrelevant',
  );
  expect(evidenceState({ ...complete, authority_basis: 'incomplete_content: short' })).toBe(
    'incomplete',
  );
  expect(evidenceState({ ...complete, excerpt_provenance: 'search_excerpt' })).toBe('snippet');
  const failed = {
    ...complete,
    excerpt_provenance: 'search_excerpt' as const,
    authority_basis:
      'source_fetch_failure=url_fetch_error; source_fetch_category=access_denied; source_fetch_http_status=403',
  };
  expect(evidenceState(failed)).toBe('failed');
  expect(retrievalDiagnostic(failed, 'en')).toBe('Publisher denied access · HTTP 403');
  expect(evidenceStateText(failed, 'hi')).toContain('पृष्ठ');
  expect(evidenceStateText(failed, 'mr')).toContain('पृष्ठ');
});

it('deduplicates visible warnings and preserves the original diagnostic list', () => {
  const warnings = [
    'source_page_unavailable:url_fetch_error',
    'source_page_required_unavailable:url_fetch_error',
    'source_page_unavailable:url_no_text',
    'llm_provider_error',
  ];
  expect(displayWarnings(warnings, 'en')).toHaveLength(2);
  expect(warnings).toHaveLength(4);
});

it('renders sanitized failure diagnostics and namesake status without claiming assessment', () => {
  const report = structuredClone(fixtures[0].verification);
  const source = report.claims[0].evidence[0];
  report.claims = [report.claims[0]];
  report.claims[0].evidence = [
    {
      ...source,
      evidence_id: 'failed',
      url: 'https://publisher.example/failure',
      excerpt_provenance: 'search_excerpt',
      what_source_says: '',
      authority_basis:
        'source_fetch_failure=url_fetch_error; source_fetch_category=access_denied; source_fetch_http_status=403',
    },
    {
      ...source,
      evidence_id: 'namesake',
      url: 'https://publisher.example/namesake',
      excerpt_provenance: 'fetched_page',
      what_source_says: '',
      authority_basis: 'entity_mismatch: missing name',
    },
  ];
  render(
    <PreferencesProvider>
      <Results result={report} />
    </PreferencesProvider>,
  );
  expect(screen.getByText('Publisher denied access · HTTP 403')).toBeVisible();
  expect(screen.getByText(/Not relevant to the exact named subject/)).toBeVisible();
  expect(screen.queryByText(/excerpt assessed/)).not.toBeInTheDocument();
  expect(relevantSources(report.claims[0])).toHaveLength(0);
});
