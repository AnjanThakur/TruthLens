// @vitest-environment node
import { afterEach, expect, it, vi } from 'vitest';
import { request } from '@/lib/api/client';
import { healthSchema } from '@/lib/api/contracts';

afterEach(() => vi.unstubAllGlobals());

it('distinguishes a deadline from connection failure and preserves user cancellation', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => {
      throw new DOMException('private timeout diagnostic', 'TimeoutError');
    }),
  );
  await expect(request('/api/health', healthSchema)).rejects.toMatchObject({ code: 'TIMEOUT' });
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => {
      throw new TypeError('private connection details');
    }),
  );
  await expect(request('/api/health', healthSchema)).rejects.toMatchObject({
    code: 'BACKEND_OFFLINE',
  });
  const aborted = new DOMException('User cancelled', 'AbortError');
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => {
      throw aborted;
    }),
  );
  await expect(request('/api/health', healthSchema)).rejects.toBe(aborted);
});
