import { z } from 'zod';
import { readJson, requireSameOrigin, responseJson, route } from '@/lib/api/server';
import { clusterSchema, draftSchema, reviewSchema } from '@/lib/alerts/contracts';
import { alertsUpstream, reviewer } from '@/lib/alerts/server';
export const dynamic = 'force-dynamic';
export function GET() {
  return route(async () => {
    await reviewer();
    const clusters = await alertsUpstream('/api/alerts/clusters', z.array(clusterSchema), 'admin');
    const drafts = await alertsUpstream('/api/alerts/drafts', z.array(draftSchema), 'admin');
    return responseJson({ clusters, drafts, publishing: false });
  });
}
export function POST(request: Request) {
  return route(async () => {
    requireSameOrigin(request);
    const { user } = await reviewer();
    const input = await readJson(request, reviewSchema, 10000);
    const { action, ...payload } = input;
    let path: string;
    let method = 'POST';
    let body: object;
    if (input.action === 'create') {
      path = `/api/alerts/clusters/${input.cluster_id}/drafts`;
      body = { language: input.language };
    } else {
      path = `/api/alerts/${input.alert_id}${action === 'edit' ? '' : '/' + action}`;
      const { alert_id: _id, ...fields } = payload as Record<string, unknown>;
      void _id;
      method = action === 'edit' ? 'PATCH' : 'POST';
      body = {
        ...fields,
        ...(['approve', 'reject'].includes(action) ? { reviewer_id: user.id } : {}),
      };
    }
    const draft = await alertsUpstream(path, draftSchema, 'admin', {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return responseJson({ draft });
  });
}
