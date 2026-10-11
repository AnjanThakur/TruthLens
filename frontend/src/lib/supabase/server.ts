import 'server-only';
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { ApiError } from '@/lib/api/errors';
export function historyConfigured() {
  return !!(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY &&
    (process.env.HISTORY_SIGNING_SECRET?.length ?? 0) >= 32
  );
}
export async function serverSupabase() {
  if (!historyConfigured()) throw new ApiError('HISTORY_DISABLED', 'History not configured.', 503);
  const jar = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      // Auth is route-handler-only; browser JavaScript never needs to read session tokens.
      cookieOptions: {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
      },
      cookies: {
        getAll: () => jar.getAll(),
        setAll: (values) =>
          values.forEach(({ name, value, options }) => jar.set(name, value, options)),
      },
    },
  );
}
export async function authenticatedSupabase() {
  const supabase = await serverSupabase();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user || user.is_anonymous)
    throw new ApiError('UNAUTHENTICATED', 'Sign in required.', 401);
  return { supabase, user };
}
