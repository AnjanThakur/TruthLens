import { explainRequestSchema, explanationSchema, validateExplanation } from '@/lib/api/contracts';
import { ApiError } from '@/lib/api/errors';
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
    const input = await readJson(request, explainRequestSchema, 1048576);
    if (isMockMode()) throw new ApiError('EXPLAIN_UNAVAILABLE', 'No synthetic translations.', 503);
    const result = await upstream('/api/explain', explanationSchema, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
      signal: request.signal,
    });
    if (result.language !== input.language || result.audience !== input.audience)
      throw new ApiError('BAD_RESPONSE', 'Explanation mismatch.', 502);
    return responseJson(validateExplanation(input.verification, result));
  });
}
