// @vitest-environment node
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { POST as contribute } from '@/app/api/alerts/contribute/route';
import { POST as withdraw } from '@/app/api/alerts/withdraw/route';
import { GET as dashboard, POST as review } from '@/app/api/alerts/review/route';
import { sourceToken, submissionToken, consentOperation } from '@/lib/alerts/server';
import { issueReceipt } from '@/lib/history/receipt';
import { verificationSchema } from '@/lib/api/contracts';
import fixture from './fixtures/person1-response.json';
const { auth } = vi.hoisted(() => ({ auth: vi.fn() }));
vi.mock('@/lib/supabase/server', () => ({
  authenticatedSupabase: auth,
  historyConfigured: () => true,
}));
const origin = 'http://localhost:3000';
const owner = '00000000-0000-4000-8000-000000000001';
const other = '00000000-0000-4000-8000-000000000002';
const fetcher = vi.fn();
function body(path: string, value: unknown, requestOrigin = origin) {
  return new Request(`${origin}/api/alerts/${path}`, {
    method: 'POST',
    headers: { Origin: requestOrigin, 'Content-Type': 'application/json' },
    body: JSON.stringify(value),
  });
}
function authorize(reviewer = false, error: unknown = null) {
  const query = {
    select: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    maybeSingle: vi.fn().mockResolvedValue({ data: reviewer ? { owner_id: owner } : null, error }),
  };
  const from = vi.fn(() => query);
  auth.mockResolvedValue({ user: { id: owner }, supabase: { from } });
  return { query, from };
}
beforeEach(() => {
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('APP_ORIGIN', origin);
  vi.stubEnv('ALERTS_BASE_URL', 'http://127.0.0.1:8001');
  vi.stubEnv('ALERTS_INGEST_TOKEN', 'i'.repeat(40));
  vi.stubEnv('ALERTS_ADMIN_TOKEN', 'a'.repeat(40));
  vi.stubEnv('ALERTS_SOURCE_SECRET', 's'.repeat(40));
  vi.stubEnv('HISTORY_SIGNING_SECRET', 'h'.repeat(40));
  auth.mockReset();
  fetcher.mockReset();
  vi.stubGlobal('fetch', fetcher);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

it('requires explicit consent and an authentic completed report, never trusting browser identities', async () => {
  authorize();
  const report = verificationSchema.parse(structuredClone(fixture));
  report.warnings = [];
  const value = { consent: true, report, receipt: issueReceipt(report) };
  expect((await contribute(body('contribute', { ...value, consent: false }))).status).toBe(400);
  expect((await contribute(body('contribute', { ...value, source_token: other }))).status).toBe(
    400,
  );
  const altered = structuredClone(report);
  altered.claims[0].verdict = 'false';
  expect((await contribute(body('contribute', { ...value, report: altered }))).status).toBe(403);
  expect((await contribute(body('contribute', value, 'https://attacker.example'))).status).toBe(
    403,
  );
  expect(fetcher).not.toHaveBeenCalled();
  fetcher.mockResolvedValue(
    Response.json({
      duplicate: false,
      deferred_reasons: ['insufficient_independent_contributors'],
    }),
  );
  const response = await contribute(body('contribute', value));
  expect(response.status).toBe(201);
  expect(await response.json()).toEqual({ accepted: true, duplicate: false, deferred: true });
  const [url, init] = fetcher.mock.calls[0];
  const payload = JSON.parse(init.body);
  expect(url.href).toBe('http://127.0.0.1:8001/api/alerts/ingest');
  expect(payload.source_token).toBe(sourceToken(owner));
  expect(payload.submission_id).toBe(submissionToken(owner, report.verification_id));
  expect(init.headers.Authorization).toBe('Bearer ' + 'i'.repeat(40));
  expect(JSON.stringify(payload)).not.toContain(owner);
});

it('refuses incomplete results and unsigned synthetic records before ingestion', async () => {
  authorize();
  const report = verificationSchema.parse(structuredClone(fixture));
  report.status = 'partial';
  const response = await contribute(
    body('contribute', { consent: true, report, receipt: issueReceipt(report) }),
  );
  expect(response.status).toBe(400);
  expect(fetcher).not.toHaveBeenCalled();
});

it('uses stable opaque per-principal identities and distinct idempotent submission IDs', () => {
  expect(sourceToken(owner)).toMatch(/^[a-f0-9-]{14}4[a-f0-9]{3}-[89ab]/);
  expect(sourceToken(owner)).toBe(sourceToken(owner));
  expect(sourceToken(owner)).not.toBe(sourceToken(other));
  expect(submissionToken(owner, 'same-report')).not.toBe(submissionToken(other, 'same-report'));
});

it('withdraws only the authenticated principal, without exposing service details', async () => {
  authorize();
  fetcher.mockResolvedValue(Response.json({ deleted_observations: 3 }));
  expect((await withdraw(body('withdraw', {}))).status).toBe(200);
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ source_token: sourceToken(owner) });
  fetcher.mockResolvedValue(
    Response.json({ error: { message: 'private storage password' } }, { status: 503 }),
  );
  const response = await withdraw(body('withdraw', {}));
  expect(response.status).toBe(503);
  expect(await response.text()).not.toContain('password');
});

it('does not grant ordinary users reviewer access and fails closed when RLS lookup fails', async () => {
  const { query } = authorize();
  expect((await dashboard()).status).toBe(403);
  expect(query.eq).toHaveBeenCalledWith('owner_id', owner);
  expect(fetcher).not.toHaveBeenCalled();
  authorize(false, { message: 'private DB diagnostic' });
  const response = await dashboard();
  expect(response.status).toBe(503);
  expect(await response.text()).not.toContain('diagnostic');
});

it('requires explicit evidence review, rejects forged reviewer IDs and preserves version conflicts', async () => {
  authorize(true);
  const value = {
    action: 'approve',
    alert_id: other,
    expected_version: 1,
    evidence_reviewed: true,
  };
  expect((await review(body('review', { ...value, evidence_reviewed: false }))).status).toBe(400);
  expect((await review(body('review', { ...value, reviewer_id: other }))).status).toBe(400);
  expect(fetcher).not.toHaveBeenCalled();
  fetcher.mockResolvedValue(
    Response.json({ error: { code: 'alerts_content_changed' } }, { status: 409 }),
  );
  const response = await review(body('review', value));
  expect(response.status).toBe(409);
  expect((await response.json()).error.code).toBe('ALERT_CONFLICT');
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
    expected_version: 1,
    evidence_reviewed: true,
    reviewer_id: owner,
  });
});

it('serializes withdrawal after pending contributions and releases failed operations', async () => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const order: string[] = [];
  const first = consentOperation(owner, async () => {
    order.push('ingest');
    await gate;
  });
  const second = consentOperation(owner, async () => {
    order.push('withdraw');
  });
  await Promise.resolve();
  expect(order).toEqual(['ingest']);
  release();
  await Promise.all([first, second]);
  expect(order).toEqual(['ingest', 'withdraw']);
  await expect(
    consentOperation(owner, async () => {
      throw new Error('fail');
    }),
  ).rejects.toThrow();
  expect(await consentOperation(owner, async () => 'recovered')).toBe('recovered');
});
