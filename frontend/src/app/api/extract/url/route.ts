import { z } from 'zod';
import { extractionSchema, publicUrlSchema } from '@/lib/api/contracts';
import { ApiError } from '@/lib/api/errors';
import { fixtureForType } from '@/lib/fixtures';
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
    const input = await readJson(request, z.object({ url: publicUrlSchema }));
    if (isMockMode()) return responseJson(fixtureForType('url').extraction);
    // Forward JSON to the fixed P1 host. Never fetch the user URL in Next.js.
    const result = await upstream('/api/extract/url', extractionSchema, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
      signal: request.signal,
    });
    if (result.text.trim().length < 10)
      throw new ApiError('EXTRACTION_EMPTY', 'No usable text.', 422);
    if (result.input_type !== 'url')
      throw new ApiError('BAD_RESPONSE', 'Unexpected input type.', 502);
    return responseJson(result);
  });
}
