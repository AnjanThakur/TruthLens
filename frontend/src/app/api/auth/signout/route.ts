import { serverSupabase } from '@/lib/supabase/server';
import { requireSameOrigin, responseJson, route } from '@/lib/api/server';
import { ApiError } from '@/lib/api/errors';
export function POST(request: Request) {
  return route(async () => {
    requireSameOrigin(request);
    const supabase = await serverSupabase();
    const { error } = await supabase.auth.signOut();
    if (error) throw new ApiError('STORAGE_ERROR', 'Sign out failed.', 503);
    return responseJson({ signed_out: true });
  });
}
