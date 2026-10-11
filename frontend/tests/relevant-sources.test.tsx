import React from 'react';
import { expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { Results } from '@/components/results';
import { PreferencesProvider } from '@/components/preferences';
import { relevantSources, warningText } from '@/lib/results';
import { fixtures } from '@/lib/fixtures';
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
