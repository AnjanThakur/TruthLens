import { z } from 'zod';
import { authenticatedSupabase } from '@/lib/supabase/server';
import { isMockMode, readJson, requireSameOrigin, responseJson, route } from '@/lib/api/server';
import { saveSchema } from '@/lib/history/contracts';
import { verifyReceipt } from '@/lib/history/receipt';
import { ApiError } from '@/lib/api/errors';
export const dynamic = 'force-dynamic';
const columns =
  'id,verification_id,input_type,input_excerpt,report_json,created_at,retention_expires_at';
export function GET(request: Request) {
  return route(async () => {
    const { supabase, user } = await authenticatedSupabase();
    const cursor = new URL(request.url).searchParams.get('cursor');
    if (cursor && !z.string().uuid().safeParse(cursor).success)
      throw new ApiError('BAD_INPUT', 'Invalid cursor.', 400);
    let query = supabase
      .from('verification_reports')
      .select(columns)
      .eq('owner_id', user.id)
      .gt('retention_expires_at', new Date().toISOString())
      .order('id', { ascending: false })
      .limit(21);
    if (cursor) query = query.lt('id', cursor);
    const { data, error } = await query;
    if (error) throw new ApiError('STORAGE_ERROR', 'History query failed.', 503);
    const rows = data ?? [];
    return responseJson({
      reports: rows.slice(0, 20),
      next_cursor: rows.length > 20 ? rows[19].id : null,
    });
  });
}
export function POST(request: Request) {
  return route(async () => {
    requireSameOrigin(request);
    const { supabase, user } = await authenticatedSupabase();
    const input = await readJson(request, saveSchema, 1048576);
    if (isMockMode()) throw new ApiError('MOCK_STORAGE', 'Mock mode cannot save.', 400);
    verifyReceipt(input.report, input.receipt);
    const now = new Date();
    const { data, error } = await supabase
      .from('verification_reports')
      .upsert(
        {
          owner_id: user.id,
          verification_id: input.report.verification_id,
          input_type: input.report.input.input_type,
          input_excerpt: input.report.input.text.slice(0, 160),
          report_json: input.report,
          consent_to_store: true,
          retention_expires_at: new Date(
            now.getTime() + input.retention_days * 86400000,
          ).toISOString(),
        },
        { onConflict: 'owner_id,verification_id', ignoreDuplicates: true },
      )
      .select('id');
    if (error) throw new ApiError('STORAGE_ERROR', 'Save failed.', 503);
    return responseJson({ saved: true, id: data?.[0]?.id ?? null }, 201);
  });
}
export function DELETE(request: Request) {
  return route(async () => {
    requireSameOrigin(request);
    const { supabase, user } = await authenticatedSupabase();
    const { id } = await readJson(request, z.object({ id: z.string().uuid() }));
    const { data, error } = await supabase
      .from('verification_reports')
      .delete()
      .eq('id', id)
      .eq('owner_id', user.id)
      .select('id');
    if (error) throw new ApiError('STORAGE_ERROR', 'Deletion failed.', 503);
    if (!data?.length)
      return responseJson({ error: { code: 'NOT_FOUND', message: 'Report not found.' } }, 404);
    return responseJson({ deleted: true });
  });
}
