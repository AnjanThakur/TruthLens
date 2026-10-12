import { NextResponse } from 'next/server';
import { serverSupabase } from '@/lib/supabase/server';
export async function GET(request: Request) {
  const url = new URL(request.url);
  const origin = process.env.APP_ORIGIN || url.origin;
  const code = url.searchParams.get('code');
  if (code) {
    try {
      const supabase = await serverSupabase();
      const { error } = await supabase.auth.exchangeCodeForSession(code);
      if (!error) return redirect(`${origin}/history`);
    } catch {
      /* No token details in logs or URL. */
    }
  }
  return redirect(`${origin}/history?auth=failed`);
}
function redirect(location: string) {
  const response = NextResponse.redirect(location);
  response.headers.set('Cache-Control', 'no-store, private');
  return response;
}
