import { verifyRequestSchema, verificationSchema, requireCompleted } from '@/lib/api/contracts';
import { ApiError } from '@/lib/api/errors';
import { fixtures, isSynthetic } from '@/lib/fixtures';
import { issueReceipt } from '@/lib/history/receipt';
import {
  isMockMode,
  readJson,
  requireSameOrigin,
  responseJson,
  route,
  upstream,
} from '@/lib/api/server';
export const dynamic = 'force-dynamic';
export function POST(request: Request) {
  return route(async () => {
    requireSameOrigin(request);
    const input = await readJson(request, verifyRequestSchema);
    const stamp = request.headers.get('x-truthlens-message-time');
    if (
      stamp &&
      (stamp.length > 64 ||
        !/(?:Z|[+-]\d{2}:\d{2})$/.test(stamp) ||
        Number.isNaN(Date.parse(stamp)))
    )
      throw new ApiError('BAD_INPUT', 'Use a valid original message timestamp.', 400);
    if (isMockMode()) {
      const fixture = fixtures.find(
        (f) =>
          f.verification.input.text === input.text &&
          f.verification.input.input_type === input.input_type,
      );
      if (!fixture) throw new ApiError('MOCK_INPUT', 'Choose an unchanged synthetic example.', 422);
      return responseJson(fixture.verification);
    }
    const result = await upstream('/api/verify', verificationSchema, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(stamp ? { 'X-TruthLens-Message-Time': stamp } : {}),
      },
      body: JSON.stringify(input),
      signal: request.signal,
    });
    let completed;
    try {
      completed = requireCompleted(result);
    } catch {
      throw new ApiError('BAD_RESPONSE', 'Unsupported status.', 502);
    }
    if (isSynthetic(completed))
      throw new ApiError('BAD_RESPONSE', 'Synthetic data in live response.', 502);
    const response = responseJson(completed);
    const receipt = issueReceipt(completed);
    if (receipt) response.headers.set('X-TruthLens-Receipt', receipt);
    return response;
  });
}
