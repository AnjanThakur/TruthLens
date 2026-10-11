// @vitest-environment node
import { afterEach, expect, it, vi } from 'vitest';
import report from './fixtures/person1-response.json';
import {
  verificationSchema,
  validateExplanation,
  verifyRequestSchema,
  extractionSchema,
} from '@/lib/api/contracts';
import { POST as verify } from '@/app/api/verify/route';
import { POST as explain } from '@/app/api/explain/route';
import { whatsappLink } from '@/lib/whatsapp';
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});
const req = (body: unknown) =>
  new Request('http://localhost:3000/api/verify', {
    method: 'POST',
    headers: { Origin: 'http://localhost:3000', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
it('retains the complete Person 1 shape and supports partial/no-checkable-claims', () => {
  expect(verificationSchema.parse(report)).toEqual(report);
  expect(verificationSchema.parse({ ...report, status: 'partial' }).status).toBe('partial');
  expect(
    verificationSchema.parse({ ...report, status: 'no_checkable_claims', claims: [] }).claims,
  ).toEqual([]);
  expect(
    extractionSchema.parse({
      ...report.input,
      extraction_details: { pages: [{ page_number: 1, text: 'test' }] },
    }).extraction_details.pages,
  ).toHaveLength(1);
  expect(verifyRequestSchema.safeParse({ text: 'test', detected_language: 'en' }).success).toBe(
    false,
  );
});
it('forwards canonical requests and preserves partial results without synthetic fallback', async () => {
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('BACKEND_BASE_URL', 'http://p1.test');
  const upstream = vi.fn<typeof fetch>(async () =>
    Response.json({ ...report, status: 'partial', warnings: ['search_unavailable'] }),
  );
  vi.stubGlobal('fetch', upstream);
  const response = await verify(
    req({
      text: report.input.text,
      input_type: 'text',
      response_language: 'en',
      audience: 'adult',
    }),
  );
  expect(response.status).toBe(200);
  expect((await response.json()).status).toBe('partial');
  const body = JSON.parse(upstream.mock.calls[0][1]!.body as string);
  expect(Object.keys(body).sort()).toEqual(
    [
      'text',
      'input_type',
      'input_language',
      'response_language',
      'audience',
      'jurisdiction',
    ].sort(),
  );
});
it('uses result/language/audience and rejects changes to evidence, context or verdict', async () => {
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('BACKEND_BASE_URL', 'http://p1.test');
  const translated = { ...report, response_language: 'hi', audience: 'senior', summary: 'सारांश' };
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => Response.json(translated)),
  );
  expect((await explain(req({ result: report, language: 'hi', audience: 'senior' }))).status).toBe(
    200,
  );
  const original = verificationSchema.parse(report);
  for (const changed of [
    { ...translated, checked_at: '2020-01-01T00:00:00Z' },
    { ...translated, claims: [] },
  ]) {
    expect(() => validateExplanation(original, changed)).toThrow();
  }
});
it('does not publish a WhatsApp link until explicitly configured', () => {
  vi.stubEnv('WHATSAPP_LINK_ENABLED', 'false');
  vi.stubEnv('WHATSAPP_PUBLIC_NUMBER', '15550000001');
  expect(whatsappLink()).toBeNull();
  vi.stubEnv('WHATSAPP_LINK_ENABLED', 'true');
  expect(whatsappLink()).toBe('https://wa.me/15550000001');
  vi.stubEnv('WHATSAPP_PUBLIC_NUMBER', 'javascript:bad');
  expect(whatsappLink()).toBeNull();
});
