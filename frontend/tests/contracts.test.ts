import { describe, expect, it } from 'vitest';
import { fixtures } from '@/lib/fixtures';
import {
  requireCompleted,
  validateExplanation,
  verificationSchema,
  verdicts,
  stances,
} from '@/lib/api/contracts';
import { isMockMode } from '@/lib/api/server';
import { validateFile } from '@/lib/api/files';

describe('document-defined verification contract', () => {
  it('accepts every fixture and covers every verdict and evidence stance', () => {
    fixtures.forEach((f) =>
      expect(verificationSchema.safeParse(f.verification).success).toBe(true),
    );
    expect(new Set(fixtures.flatMap((f) => f.verification.claims.map((c) => c.verdict)))).toEqual(
      new Set(verdicts),
    );
    expect(
      new Set(
        fixtures.flatMap((f) =>
          f.verification.claims.flatMap((c) => c.evidence.map((e) => e.stance)),
        ),
      ),
    ).toEqual(new Set(stances));
  });
  it('rejects renamed verdicts and missing required attribution', () => {
    const result = structuredClone(fixtures[0].verification);
    expect(
      verificationSchema.safeParse({
        ...result,
        claims: [{ ...result.claims[0], verdict: 'fake' }],
      }).success,
    ).toBe(false);
    expect(
      verificationSchema.safeParse({
        ...result,
        claims: [{ ...result.claims[0], evidence: [{ title: 'Missing source' }] }],
      }).success,
    ).toBe(false);
  });
  it('accepts unknown dates, empty evidence and zero factual claims', () => {
    const result = structuredClone(fixtures[0].verification);
    result.claims[0].evidence[0].published_at = null;
    expect(verificationSchema.parse(result).claims[0].evidence[0].published_at).toBeNull();
    expect(fixtures[5].verification.claims[0].evidence).toHaveLength(0);
    expect(verificationSchema.parse({ ...result, claims: [] }).claims).toHaveLength(0);
  });
  it('rejects unsafe evidence links and incomplete transport results', () => {
    const result = structuredClone(fixtures[0].verification);
    result.claims[0].evidence[0].url = 'javascript:alert(1)';
    expect(verificationSchema.safeParse(result).success).toBe(false);
    expect(() => requireCompleted({ ...fixtures[0].verification, status: 'pending' })).toThrow();
  });
  it('never enables fixture API in production', () => {
    expect(
      isMockMode({
        NODE_ENV: 'production',
        USE_MOCK_API: 'true',
        NEXT_PUBLIC_USE_MOCK_API: 'true',
      }),
    ).toBe(false);
    expect(
      isMockMode({
        NODE_ENV: 'development',
        USE_MOCK_API: 'true',
        NEXT_PUBLIC_USE_MOCK_API: 'true',
      }),
    ).toBe(true);
    expect(isMockMode({ NODE_ENV: 'development', USE_MOCK_API: 'true' })).toBe(false);
  });
  it('only accepts explanation projections matching original claim identities', () => {
    const original = fixtures[0].verification;
    const rewritten = {
      verification_id: original.verification_id,
      language: 'hi',
      audience: 'easy',
      summary: 'सारांश',
      claims: original.claims.map((c) => ({
        claim_id: c.claim_id,
        explanation: 'विवरण',
        short_summary: 'सारांश',
        next_step: 'अगला कदम',
        verdict: 'false',
        evidence: [],
      })),
    };
    const before = structuredClone(original);
    const display = validateExplanation(original, rewritten);
    expect(original).toEqual(before);
    expect(display.claims[0]).not.toHaveProperty('verdict');
    expect(() => validateExplanation(original, { ...rewritten, claims: [] })).toThrow();
  });
});
describe('file validation', () => {
  it('accepts supported MIME, rejects oversized, empty and mismatched uploads', () => {
    expect(validateFile({ size: 20, type: 'audio/ogg' }, 'audio')).toBe('audio');
    expect(() => validateFile({ size: 20, type: 'text/html' })).toThrow();
    expect(() => validateFile({ size: 0, type: 'image/png' })).toThrow();
    expect(() => validateFile({ size: 200, type: 'image/png' }, 'pdf')).toThrow();
    expect(() => validateFile({ size: 20000000, type: 'image/png' })).toThrow();
  });
});
