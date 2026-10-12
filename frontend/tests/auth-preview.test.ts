// @vitest-environment node
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { GET } from '@/app/auth/callback/route';
import { serverSupabase, authenticatedSupabase } from '@/lib/supabase/server';
import { requireSameOrigin } from '@/lib/api/server';
const { client, jar } = vi.hoisted(() => ({
  client: vi.fn(),
  jar: { getAll: vi.fn(() => []), set: vi.fn() },
}));
vi.mock('@supabase/ssr', () => ({ createServerClient: client }));
vi.mock('next/headers', () => ({ cookies: async () => jar }));
beforeEach(() => {
  vi.stubEnv('NODE_ENV', 'production');
  vi.stubEnv('APP_ORIGIN', 'http://127.0.0.1:3001');
  vi.stubEnv('NEXT_PUBLIC_SUPABASE_URL', 'https://offline-project.supabase.co');
  vi.stubEnv('NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY', 'offline-publishable');
  vi.stubEnv('HISTORY_SIGNING_SECRET', 'offline-key-'.repeat(4));
  client.mockReset();
  jar.set.mockReset();
});
afterEach(() => vi.unstubAllEnvs());

it('uses the configured project and preserves secure, httpOnly host-scoped cookies', async () => {
  client.mockReturnValue({});
  await serverSupabase();
  const [url, key, options] = client.mock.calls[0];
  expect(url).toBe('https://offline-project.supabase.co');
  expect(key).toBe('offline-publishable');
  expect(options.cookieOptions).toEqual({
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
  });
  options.cookies.setAll([{ name: 'offline-session', value: 'offline-value', options: {} }]);
  expect(jar.set).toHaveBeenCalledWith('offline-session', 'offline-value', {});
});

it.each(['http://127.0.0.1:3001', 'http://localhost:3001'])(
  'keeps callback redirects on %s and never caches them or reflects codes',
  async (origin) => {
    vi.stubEnv('APP_ORIGIN', origin);
    const exchange = vi.fn().mockResolvedValue({ error: null });
    client.mockReturnValue({ auth: { exchangeCodeForSession: exchange } });
    const response = await GET(
      new Request(`${origin}/auth/callback?code=offline-code&next=https://attacker.test`),
    );
    expect(exchange).toHaveBeenCalledWith('offline-code');
    expect(response.headers.get('location')).toBe(`${origin}/history`);
    expect(response.headers.get('cache-control')).toBe('no-store, private');
  },
);

it('keeps CSRF checks strict when the localhost preview origin is selected', () => {
  vi.stubEnv('APP_ORIGIN', 'http://localhost:3001');
  for (const origin of [
    'http://localhost:3000',
    'http://127.0.0.1:3001',
    'https://attacker.test',
  ]) {
    expect(() =>
      requireSameOrigin(
        new Request('http://localhost:3001/api/history', {
          headers: { Origin: origin },
        }),
      ),
    ).toThrow();
  }
  expect(() =>
    requireSameOrigin(
      new Request('http://localhost:3001/api/history', {
        headers: { Origin: 'http://localhost:3001' },
      }),
    ),
  ).not.toThrow();
});

it('fails safely on a rejected callback without redirecting to port 3000', async () => {
  client.mockReturnValue({
    auth: { exchangeCodeForSession: async () => ({ error: { message: 'private diagnostic' } }) },
  });
  const response = await GET(new Request('http://127.0.0.1:3001/auth/callback?code=offline-code'));
  expect(response.headers.get('location')).toBe('http://127.0.0.1:3001/history?auth=failed');
  expect(response.headers.get('cache-control')).toContain('no-store');
  expect(await response.text()).not.toContain('private diagnostic');
});

it('rejects anonymous users and failed server-validated authentication', async () => {
  for (const result of [
    { data: { user: { id: 'offline-user', is_anonymous: true } }, error: null },
    { data: { user: null }, error: { message: 'invalid session' } },
  ]) {
    client.mockReturnValue({ auth: { getUser: async () => result } });
    await expect(authenticatedSupabase()).rejects.toMatchObject({ code: 'UNAUTHENTICATED' });
  }
});
