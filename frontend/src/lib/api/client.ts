import type { z } from 'zod';
import { ApiError, errorMessage } from './errors';
import { CLIENT_TIMEOUT_MS } from './timeouts';
import {
  extractionSchema,
  requireCompleted,
  validateExplanation,
  explanationSchema,
  type Verification,
  type VerifyRequest,
  type Language,
} from './contracts';

export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
  onResponse?: (response: Response) => void,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      cache: 'no-store',
      signal: init?.signal
        ? AbortSignal.any([init.signal, AbortSignal.timeout(CLIENT_TIMEOUT_MS)])
        : AbortSignal.timeout(CLIENT_TIMEOUT_MS),
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    const code =
      error instanceof Error && error.name === 'TimeoutError' ? 'TIMEOUT' : 'BACKEND_OFFLINE';
    throw new ApiError(code, errorMessage(code));
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const code = body?.error?.code ?? (response.status === 429 ? 'RATE_LIMIT' : 'BAD_RESPONSE');
    throw new ApiError(code, errorMessage(code), response.status);
  }
  const parsed = schema.safeParse(body);
  if (!parsed.success) throw new ApiError('BAD_RESPONSE', errorMessage('BAD_RESPONSE'));
  onResponse?.(response);
  return parsed.data;
}
export const jsonRequest = (value: unknown, signal?: AbortSignal): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(value),
  signal,
});
export async function verify(input: VerifyRequest, signal: AbortSignal, messageTime?: string) {
  const { verificationSchema } = await import('./contracts');
  let receipt: string | null = null;
  const result = requireCompleted(
    await request(
      '/api/verify',
      verificationSchema,
      {
        ...jsonRequest(input, signal),
        headers: {
          'Content-Type': 'application/json',
          ...(messageTime ? { 'X-TruthLens-Message-Time': messageTime } : {}),
        },
      },
      (response) => {
        receipt = response.headers.get('X-TruthLens-Receipt');
      },
    ),
  );
  return { result, receipt };
}
export function extractFile(file: File, signal: AbortSignal) {
  const body = new FormData();
  body.set('file', file);
  return request('/api/extract', extractionSchema, { method: 'POST', body, signal });
}
export function extractUrl(url: string, signal: AbortSignal) {
  return request('/api/extract/url', extractionSchema, jsonRequest({ url }, signal));
}
export async function explain(
  verification: Verification,
  language: Language,
  audience: 'standard' | 'easy',
  signal: AbortSignal,
) {
  return validateExplanation(
    verification,
    await request(
      '/api/explain',
      explanationSchema,
      jsonRequest(
        { result: verification, language, audience: audience === 'easy' ? 'senior' : 'adult' },
        signal,
      ),
    ),
  );
}
