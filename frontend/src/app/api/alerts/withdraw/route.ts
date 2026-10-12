import { z } from 'zod';
import { authenticatedSupabase } from '@/lib/supabase/server';
import { requireSameOrigin, responseJson, route } from '@/lib/api/server';
import { alertsUpstream, consentOperation, sourceToken } from '@/lib/alerts/server';
export function POST(request: Request) {
  return route(async () => {
    requireSameOrigin(request);
    const { user } = await authenticatedSupabase();
    await consentOperation(user.id, () =>
      alertsUpstream(
        '/api/alerts/withdraw',
        z.object({ deleted_observations: z.number().int().nonnegative() }),
        'ingest',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source_token: sourceToken(user.id) }),
        },
      ),
    );
    return responseJson({ withdrawn: true });
  });
}
