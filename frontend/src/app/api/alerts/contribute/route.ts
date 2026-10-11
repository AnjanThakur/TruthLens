import { z } from 'zod';
import { ApiError } from '@/lib/api/errors';
import { isMockMode, readJson, requireSameOrigin, responseJson, route } from '@/lib/api/server';
import { authenticatedSupabase } from '@/lib/supabase/server';
import { verifyReceipt } from '@/lib/history/receipt';
import { contributeSchema } from '@/lib/alerts/contracts';
import {
  alertsUpstream,
  consentOperation,
  sourceToken,
  submissionToken,
} from '@/lib/alerts/server';
export const dynamic = 'force-dynamic';
export function POST(request: Request) {
  return route(async () => {
    requireSameOrigin(request);
    const { user } = await authenticatedSupabase();
    const input = await readJson(request, contributeSchema, 262000);
    if (isMockMode())
      throw new ApiError('MOCK_STORAGE', 'Synthetic reports cannot contribute.', 400);
    verifyReceipt(input.report, input.receipt);
    if (input.report.status !== 'completed' || input.report.warnings.length)
      throw new ApiError('BAD_INPUT', 'Only completed reports can contribute.', 400);
    const result = await consentOperation(user.id, () =>
      alertsUpstream(
        '/api/alerts/ingest',
        z.object({ duplicate: z.boolean(), deferred_reasons: z.array(z.string()) }),
        'ingest',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            consent: true,
            source_token: sourceToken(user.id),
            submission_id: submissionToken(user.id, input.report.verification_id),
            verification: input.report,
          }),
        },
      ),
    );
    return responseJson(
      { accepted: true, duplicate: result.duplicate, deferred: !!result.deferred_reasons.length },
      201,
    );
  });
}
