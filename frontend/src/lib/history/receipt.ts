import 'server-only';
import { createHmac, timingSafeEqual } from 'node:crypto';
import type { Verification } from '@/lib/api/contracts';
import { ApiError } from '@/lib/api/errors';
import { isSynthetic } from '@/lib/fixtures';
const secret = () => process.env.HISTORY_SIGNING_SECRET;
export function issueReceipt(result: Verification) {
  const key = secret();
  if (!key || key.length < 32 || isSynthetic(result)) return null;
  const expiry = Date.now() + 60 * 60 * 1000;
  return `${expiry}.${createHmac('sha256', key)
    .update(`${expiry}:${JSON.stringify(result)}`)
    .digest('hex')}`;
}
export function verifyReceipt(result: Verification, receipt: string, now = Date.now()) {
  if (isSynthetic(result)) throw new ApiError('MOCK_STORAGE', 'Synthetic report.', 400);
  const key = secret();
  if (!key || key.length < 32)
    throw new ApiError('HISTORY_DISABLED', 'History requires a signing key.', 503);
  const [expiry, signature] = receipt.split('.');
  const timestamp = Number(expiry);
  if (
    !Number.isFinite(timestamp) ||
    timestamp < now ||
    timestamp > now + 3600000 ||
    !/^[a-f0-9]{64}$/.test(signature || '')
  )
    throw new ApiError('FORBIDDEN', 'Invalid receipt.', 403);
  const expected = createHmac('sha256', key)
    .update(`${expiry}:${JSON.stringify(result)}`)
    .digest();
  if (!timingSafeEqual(expected, Buffer.from(signature, 'hex')))
    throw new ApiError('FORBIDDEN', 'Invalid receipt.', 403);
}
