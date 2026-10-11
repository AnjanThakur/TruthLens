import 'server-only';
import type { z } from 'zod';
import { ApiError, errorMessage } from './errors';

export function isMockMode(env = process.env) {
  return (
    env.NODE_ENV !== 'production' &&
    env.USE_MOCK_API === 'true' &&
    env.NEXT_PUBLIC_USE_MOCK_API === 'true'
  );
}
export function responseJson(value: unknown, status = 200) {
  return Response.json(value, { status, headers: { 'Cache-Control': 'no-store, private' } });
}
export async function route(action: () => Promise<Response>) {
  try {
    return await action();
  } catch (error) {
    const known = error instanceof ApiError;
    const code = known ? error.code : 'BAD_RESPONSE';
    return responseJson(
      { error: { code, message: errorMessage(code) } },
      known ? error.status : 502,
    );
  }
}
export function requireSameOrigin(request: Request) {
  const origin = request.headers.get('origin');
  const expected = process.env.APP_ORIGIN || new URL(request.url).origin;
  if (!origin || origin !== expected)
    throw new ApiError('FORBIDDEN', errorMessage('FORBIDDEN'), 403);
}
export async function readJson<T>(
  request: Request,
  schema: z.ZodType<T>,
  maximum = 256000,
): Promise<T> {
  if (!request.headers.get('content-type')?.startsWith('application/json'))
    throw new ApiError('BAD_INPUT', errorMessage('BAD_INPUT'), 415);
  const reader = request.body?.getReader();
  if (!reader) throw new ApiError('BAD_INPUT', errorMessage('BAD_INPUT'), 400);
  const chunks: Uint8Array[] = [];
  let bytes = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    bytes += value.length;
    if (bytes > maximum) {
      await reader.cancel();
      throw new ApiError('BAD_INPUT', errorMessage('BAD_INPUT'), 413);
    }
    chunks.push(value);
  }
  try {
    return schema.parse(JSON.parse(Buffer.concat(chunks).toString('utf8')));
  } catch {
    throw new ApiError('BAD_INPUT', errorMessage('BAD_INPUT'), 400);
  }
}
export async function upstream<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const base = process.env.BACKEND_BASE_URL;
  if (!base) throw new ApiError('NOT_CONFIGURED', errorMessage('NOT_CONFIGURED'), 503);
  const url = new URL(base);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password)
    throw new ApiError('NOT_CONFIGURED', errorMessage('NOT_CONFIGURED'), 503);
  let response: Response;
  try {
    response = await fetch(new URL(path, url), {
      ...init,
      cache: 'no-store',
      redirect: 'error',
      headers: {
        ...Object.fromEntries(new Headers(init?.headers).entries()),
        ...(process.env.BACKEND_API_TOKEN
          ? { Authorization: `Bearer ${process.env.BACKEND_API_TOKEN}` }
          : {}),
      },
      signal: init?.signal
        ? AbortSignal.any([
            init.signal,
            AbortSignal.timeout(Number(process.env.BACKEND_TIMEOUT_MS) || 60000),
          ])
        : AbortSignal.timeout(Number(process.env.BACKEND_TIMEOUT_MS) || 60000),
    });
  } catch (error) {
    const code =
      error instanceof Error && error.name === 'TimeoutError' ? 'TIMEOUT' : 'BACKEND_OFFLINE';
    throw new ApiError(code, errorMessage(code), code === 'TIMEOUT' ? 504 : 503);
  }
  if (!response.ok) {
    const code =
      response.status === 429
        ? 'RATE_LIMIT'
        : response.status === 413
          ? 'UPLOAD_TOO_LARGE'
          : response.status === 415
            ? 'UNSUPPORTED_FILE'
            : response.status >= 500
              ? 'BACKEND_OFFLINE'
              : 'BAD_INPUT';
    throw new ApiError(code, errorMessage(code), response.status);
  }
  const reader = response.body?.getReader();
  if (!reader) throw new ApiError('BAD_RESPONSE', errorMessage('BAD_RESPONSE'), 502);
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.length;
      if (total > 2097152) {
        await reader.cancel();
        throw new ApiError('BAD_RESPONSE', errorMessage('BAD_RESPONSE'), 502);
      }
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('TIMEOUT', errorMessage('TIMEOUT'), 504);
  }
  let payload: unknown;
  try {
    payload = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    throw new ApiError('BAD_RESPONSE', errorMessage('BAD_RESPONSE'), 502);
  }
  const result = schema.safeParse(payload);
  if (!result.success) throw new ApiError('BAD_RESPONSE', errorMessage('BAD_RESPONSE'), 502);
  return result.data;
}
