// @vitest-environment node
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { POST, DELETE } from '@/app/api/history/route';
import { issueReceipt } from '@/lib/history/receipt';
import { verificationSchema } from '@/lib/api/contracts';
import fixture from './fixtures/person1-response.json';
const { auth } = vi.hoisted(() => ({ auth: vi.fn() }));
vi.mock('@/lib/supabase/server', () => ({ authenticatedSupabase: auth }));
const origin = 'http://localhost:3000';
const owner = '00000000-0000-4000-8000-000000000001';
const id = '00000000-0000-4000-8000-000000000002';
const report = () => verificationSchema.parse(structuredClone(fixture));
function request(method: string, body: unknown, requestOrigin = origin) {
  return new Request(`${origin}/api/history`, {
    method,
    headers: { Origin: requestOrigin, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
function database(data: unknown[] = [{ id }], error: unknown = null) {
  const query = {
    upsert: vi.fn().mockReturnThis(),
    delete: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    select: vi.fn().mockResolvedValue({ data, error }),
  };
  const from = vi.fn(() => query);
  auth.mockResolvedValue({ user: { id: owner }, supabase: { from } });
  return { query, from };
}
beforeEach(() => {
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('APP_ORIGIN', origin);
  vi.stubEnv('HISTORY_SIGNING_SECRET', 'offline-history-test-key-'.repeat(3));
  auth.mockReset();
});
afterEach(() => vi.unstubAllEnvs());

it('saves only an explicitly consented signed report under the authenticated owner', async () => {
  const { query } = database();
  const result = report();
  const response = await POST(
    request('POST', {
      report: result,
      receipt: issueReceipt(result),
      consent_to_store: true,
      retention_days: 7,
      owner_id: 'attacker-supplied-owner',
    }),
  );
  expect(response.status).toBe(201);
  expect(query.upsert.mock.calls[0][0]).toMatchObject({
    owner_id: owner,
    consent_to_store: true,
    report_json: result,
  });
  expect(query.upsert.mock.calls[0][1]).toMatchObject({ ignoreDuplicates: true });
  expect(response.headers.get('Cache-Control')).toContain('no-store');
});

it('rejects missing consent, altered reports and expired receipts before database writes', async () => {
  const { from } = database();
  const result = report();
  const receipt = issueReceipt(result);
  const body = { report: result, receipt, consent_to_store: true, retention_days: 7 };
  expect((await POST(request('POST', { ...body, consent_to_store: false }))).status).toBe(400);
  const changed = structuredClone(result);
  changed.claims[0].verdict = 'false';
  expect((await POST(request('POST', { ...body, report: changed }))).status).toBe(403);
  expect((await POST(request('POST', { ...body, receipt: '1.' + '0'.repeat(64) }))).status).toBe(
    403,
  );
  expect(from).not.toHaveBeenCalled();
});

it('scopes deletion to the authenticated owner and conceals inaccessible records', async () => {
  const { query } = database([]);
  const response = await DELETE(request('DELETE', { id }));
  expect(response.status).toBe(404);
  expect(query.eq).toHaveBeenCalledWith('owner_id', owner);
  expect(query.eq).toHaveBeenCalledWith('id', id);
  expect((await DELETE(request('DELETE', { id }, 'https://attacker.test'))).status).toBe(403);
});

it('does not expose Supabase diagnostics in a storage failure', async () => {
  database([], { message: 'private database connection diagnostic' });
  const response = await DELETE(request('DELETE', { id }));
  expect(response.status).toBe(503);
  expect(await response.text()).not.toContain('private database');
});
