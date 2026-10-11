// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { POST as verifyRoute } from '@/app/api/verify/route';
import { POST as explainRoute } from '@/app/api/explain/route';
import { POST as urlRoute } from '@/app/api/extract/url/route';
import { GET as historyRoute } from '@/app/api/history/route';
import { fixtures } from '@/lib/fixtures';
import { requireSameOrigin } from '@/lib/api/server';
import { ApiError } from '@/lib/api/errors';
vi.mock('@/lib/supabase/server', () => ({
  authenticatedSupabase: vi.fn(async () => {
    throw new ApiError('UNAUTHENTICATED', 'Sign in.', 401);
  }),
}));
const origin = 'http://localhost:3000';
const input = { text: fixtures[0].verification.input.text, input_type: 'text' };
function req(path: string, body: unknown, requestOrigin = origin) {
  return new Request(`${origin}${path}`, {
    method: 'POST',
    headers: { Origin: requestOrigin, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
function backendResult() {
  const report = structuredClone(fixtures[0].verification);
  report.verification_id = 'adapter-contract-test';
  report.warnings = [];
  report.claims.forEach((c) =>
    c.evidence.forEach((e) => {
      e.source_type = 'adapter_test';
    }),
  );
  return report;
}
beforeEach(() => {
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('BACKEND_BASE_URL', 'http://p1.test');
  vi.stubEnv('USE_MOCK_API', 'true');
  vi.stubEnv('NEXT_PUBLIC_USE_MOCK_API', 'true');
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});
describe('live proxy isolation and errors', () => {
  it('production ignores fixture flags, calls fixed upstream and signs the live snapshot', async () => {
    vi.stubEnv('HISTORY_SIGNING_SECRET', 'test-secret'.repeat(5));
    const fetch = vi.fn<typeof globalThis.fetch>(async () => Response.json(backendResult()));
    vi.stubGlobal('fetch', fetch);
    const response = await verifyRoute(req('/api/verify', input));
    expect(response.status).toBe(200);
    expect(response.headers.get('X-TruthLens-Receipt')).toBeTruthy();
    expect(String(fetch.mock.calls[0][0])).toBe('http://p1.test/api/verify');
    expect(response.headers.get('Cache-Control')).toContain('no-store');
  });
  it('rejects synthetic data returned by a live upstream', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Response.json(fixtures[0].verification)),
    );
    expect((await verifyRoute(req('/api/verify', input))).status).toBe(502);
  });
  it.each([429, 500])('returns honest errors for upstream HTTP %i', async (status) => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('private stack trace', { status })),
    );
    const response = await verifyRoute(req('/api/verify', input));
    const body = await response.json();
    expect(response.status).toBe(status);
    expect(JSON.stringify(body)).not.toContain('private stack trace');
    expect(body).not.toHaveProperty('claims');
  });
  it('handles offline, timeout, malformed and empty-claim results', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('connection refused');
      }),
    );
    expect((await verifyRoute(req('/api/verify', input))).status).toBe(503);
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new DOMException('deadline', 'TimeoutError');
      }),
    );
    expect((await verifyRoute(req('/api/verify', input))).status).toBe(504);
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Response.json({ claims: [] })),
    );
    expect((await verifyRoute(req('/api/verify', input))).status).toBe(502);
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Response.json({ ...backendResult(), claims: [] })),
    );
    expect((await verifyRoute(req('/api/verify', input))).status).toBe(200);
  });
  it('never fetches a submitted URL directly and enforces URL extraction type', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(async () => Response.json(fixtures[4].extraction));
    vi.stubGlobal('fetch', fetch);
    expect(
      (await urlRoute(req('/api/extract/url', { url: 'https://example.org/user-article' }))).status,
    ).toBe(200);
    expect(String(fetch.mock.calls[0][0])).toBe('http://p1.test/api/extract/url');
    expect((await urlRoute(req('/api/extract/url', { url: 'file:///private' }))).status).toBe(400);
  });
  it('rejects cross-origin mutations and unauthenticated history access', async () => {
    expect(() => requireSameOrigin(req('/api/verify', input, 'https://attacker.test'))).toThrow();
    expect((await verifyRoute(req('/api/verify', input, 'https://attacker.test'))).status).toBe(
      403,
    );
    expect((await historyRoute(new Request(`${origin}/api/history`))).status).toBe(401);
  });
  it('rejects rewritten explanation identities rather than replacing facts', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        Response.json({
          verification_id: 'wrong',
          language: 'hi',
          audience: 'easy',
          summary: 'test',
          claims: [],
        }),
      ),
    );
    expect(
      (
        await explainRoute(
          req('/api/explain', { verification: backendResult(), language: 'hi', audience: 'easy' }),
        )
      ).status,
    ).toBe(502);
  });
});
