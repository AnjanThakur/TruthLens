// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest';
import { fixtures } from '@/lib/fixtures';
import { issueReceipt, verifyReceipt } from '@/lib/history/receipt';
afterEach(() => vi.unstubAllEnvs());
function realResult() {
  const report = structuredClone(fixtures[0].verification);
  report.verification_id = 'live-contract-test';
  report.warnings = [];
  report.claims.forEach((c) =>
    c.evidence.forEach((e) => {
      e.source_type = 'official';
    }),
  );
  return report;
}
describe('history report authenticity boundary', () => {
  it('signs live results and accepts their unaltered snapshot', () => {
    vi.stubEnv('HISTORY_SIGNING_SECRET', 'test-key-'.repeat(8));
    const report = realResult();
    const receipt = issueReceipt(report)!;
    expect(receipt).toBeTruthy();
    expect(() => verifyReceipt(report, receipt)).not.toThrow();
  });
  it('rejects changed claims, evidence, expired receipts and synthetic results', () => {
    vi.stubEnv('HISTORY_SIGNING_SECRET', 'test-key-'.repeat(8));
    const report = realResult();
    const receipt = issueReceipt(report)!;
    const changed = structuredClone(report);
    changed.claims[0].verdict = 'false';
    expect(() => verifyReceipt(changed, receipt)).toThrow();
    changed.claims[0] = structuredClone(report.claims[0]);
    changed.claims[0].evidence[0].url = 'https://example.org/changed';
    expect(() => verifyReceipt(changed, receipt)).toThrow();
    expect(() => verifyReceipt(report, receipt, Date.now() + 3700000)).toThrow();
    expect(issueReceipt(fixtures[0].verification)).toBeNull();
    expect(() => verifyReceipt(fixtures[0].verification, receipt)).toThrow();
  });
  it('disables save receipts without server-only key configuration', () => {
    vi.stubEnv('HISTORY_SIGNING_SECRET', '');
    expect(issueReceipt(realResult())).toBeNull();
    expect(() => verifyReceipt(realResult(), 'bad')).toThrow();
  });
});
