import 'server-only';
import { createHmac } from 'node:crypto';
import type { z } from 'zod';
import { ApiError } from '@/lib/api/errors';
import { upstream } from '@/lib/api/server';
import { authenticatedSupabase, historyConfigured } from '@/lib/supabase/server';

export function alertsConfigured() {
  return (
    historyConfigured() &&
    !!process.env.ALERTS_BASE_URL &&
    (process.env.ALERTS_INGEST_TOKEN?.length ?? 0) >= 32 &&
    (process.env.ALERTS_SOURCE_SECRET?.length ?? 0) >= 32
  );
}
export function sourceToken(owner: string) {
  return opaqueToken(`source:${owner}`);
}
export function submissionToken(owner: string, verificationId: string) {
  return opaqueToken(`submission:${owner}:${verificationId}`);
}
function opaqueToken(value: string) {
  const key = process.env.ALERTS_SOURCE_SECRET;
  if (!key || key.length < 32) throw new ApiError('NOT_CONFIGURED', 'Alerts not configured.', 503);
  const bytes = createHmac('sha256', key)
    .update(`truthlens-consented-alert:${value}`)
    .digest()
    .subarray(0, 16);
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const hex = bytes.toString('hex');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
export async function reviewer() {
  const context = await authenticatedSupabase();
  const { data, error } = await context.supabase
    .from('alert_reviewers')
    .select('owner_id')
    .eq('owner_id', context.user.id)
    .maybeSingle();
  if (error) throw new ApiError('STORAGE_ERROR', 'Reviewer access could not be checked.', 503);
  if (!data) throw new ApiError('FORBIDDEN', 'Reviewer access required.', 403);
  return context;
}
export function alertsUpstream<T>(
  path: string,
  schema: z.ZodType<T>,
  role: 'ingest' | 'admin',
  init?: RequestInit,
) {
  const token = role === 'admin' ? process.env.ALERTS_ADMIN_TOKEN : process.env.ALERTS_INGEST_TOKEN;
  if (!process.env.ALERTS_BASE_URL || !token || token.length < 32)
    throw new ApiError('NOT_CONFIGURED', 'Alerts not configured.', 503);
  return upstream(path, schema, init, { base: process.env.ALERTS_BASE_URL, token, timeout: 15000 });
}

// Single website process: serialize contribution and withdrawal for one principal.
// Keys are removed after the last waiter; identities never leave this server module.
const pending = new Map<string, { tail: Promise<void>; count: number }>();
export async function consentOperation<T>(owner: string, operation: () => Promise<T>): Promise<T> {
  let entry = pending.get(owner);
  if (!entry) {
    if (pending.size >= 128) throw new ApiError('RATE_LIMIT', 'Please retry later.', 429);
    entry = { tail: Promise.resolve(), count: 0 };
    pending.set(owner, entry);
  }
  if (entry.count >= 4) throw new ApiError('RATE_LIMIT', 'Please retry later.', 429);
  entry.count++;
  const previous = entry.tail;
  let release!: () => void;
  entry.tail = new Promise<void>((resolve) => {
    release = resolve;
  });
  await previous;
  try {
    return await operation();
  } finally {
    release();
    if (--entry.count === 0) pending.delete(owner);
  }
}
