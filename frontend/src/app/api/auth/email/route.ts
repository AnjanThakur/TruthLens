import { z } from 'zod';
import { serverSupabase } from '@/lib/supabase/server';
import { readJson, requireSameOrigin, responseJson, route } from '@/lib/api/server';
import { ApiError } from '@/lib/api/errors';
export function POST(request: Request) {
  return route(async () => {
    requireSameOrigin(request);
    const { email } = await readJson(request, z.object({ email: z.string().email().max(254) }));
    const origin = process.env.APP_ORIGIN || new URL(request.url).origin;
    const supabase = await serverSupabase();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${origin}/auth/callback` },
    });
    if (error)
      throw new ApiError(
        error.status === 429 ? 'RATE_LIMIT' : 'STORAGE_ERROR',
        'Unable to send sign-in link.',
        503,
      );
    return responseJson({ sent: true });
  });
}
