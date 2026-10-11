import { healthSchema } from '@/lib/api/contracts';
import { isMockMode, responseJson, route, upstream } from '@/lib/api/server';
export const dynamic = 'force-dynamic';
export function GET() {
  return route(async () =>
    responseJson(
      isMockMode()
        ? {
            status: 'synthetic',
            capabilities: {
              extract: ['image', 'audio', 'pdf', 'url'],
              verify: true,
              explain: false,
            },
          }
        : await upstream('/api/health', healthSchema),
    ),
  );
}
