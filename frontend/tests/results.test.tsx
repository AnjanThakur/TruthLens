import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Results } from '@/components/results';
import { PreferencesProvider } from '@/components/preferences';
import { fixtures } from '@/lib/fixtures';
describe('evidence presentation', () => {
  it('renders independent verdicts and attributable source links', () => {
    render(
      <PreferencesProvider>
        <Results result={fixtures[0].verification} />
      </PreferencesProvider>,
    );
    expect(screen.getByText('Verified')).toBeVisible();
    expect(screen.getByText('False')).toBeVisible();
    expect(screen.getAllByRole('article')).toHaveLength(2);
    const sources = screen.getAllByRole('link', {
      name: /Synthetic test notice.*View original source/,
    });
    expect(sources).toHaveLength(2);
    sources.forEach((link) => expect(link).toHaveAttribute('rel', 'noopener noreferrer'));
    expect(screen.getAllByText('FICTIONAL TEST PUBLISHER — NOT A REAL SOURCE')).toHaveLength(2);
  });
  it('keeps unconfirmed distinct from false and never creates missing citations', () => {
    render(
      <PreferencesProvider>
        <Results result={fixtures[5].verification} />
      </PreferencesProvider>,
    );
    expect(screen.getByText('Unconfirmed')).toBeVisible();
    expect(screen.queryByText('False')).not.toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText(/A lack of evidence does not prove it false/)).toBeVisible();
  });
  it('shows absent source dates honestly and conflicting evidence separately', () => {
    const report = structuredClone(fixtures[3].verification);
    report.claims[0].evidence[0].published_at = null;
    render(
      <PreferencesProvider>
        <Results result={report} />
      </PreferencesProvider>,
    );
    expect(screen.getByText('Date not provided')).toBeVisible();
    expect(screen.getByText('Adds context')).toBeVisible();
    expect(screen.getByText('Contradicts')).toBeVisible();
  });
});
