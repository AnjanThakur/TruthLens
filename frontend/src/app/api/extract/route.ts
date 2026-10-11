import { extractionSchema } from '@/lib/api/contracts';
import { validateFile } from '@/lib/api/files';
import { ApiError } from '@/lib/api/errors';
import { fixtureForType } from '@/lib/fixtures';
import {
  isMockMode,
  requireSameOrigin,
  responseJson,
  route,
  upstream,
  serverUploadLimit,
} from '@/lib/api/server';
export const dynamic = 'force-dynamic';
export function POST(request: Request) {
  return route(async () => {
    requireSameOrigin(request);
    const maximum = serverUploadLimit();
    if (Number(request.headers.get('content-length') || 0) > maximum + 65536)
      throw new ApiError('UPLOAD_TOO_LARGE', 'Upload too large.', 413);
    // Bound streamed multipart body before parsing; do not trust Content-Length.
    const reader = request.body?.getReader();
    if (!reader) throw new ApiError('BAD_INPUT', 'Missing body.', 400);
    const chunks: Uint8Array[] = [];
    let total = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.length;
      if (total > maximum + 65536) {
        await reader.cancel();
        throw new ApiError('UPLOAD_TOO_LARGE', 'Upload too large.', 413);
      }
      chunks.push(value);
    }
    let form: FormData;
    try {
      form = await new Response(Buffer.concat(chunks), {
        headers: { 'Content-Type': request.headers.get('content-type') || '' },
      }).formData();
    } catch {
      throw new ApiError('BAD_INPUT', 'Invalid multipart body.', 400);
    }
    const file = form.get('file');
    if (!(file instanceof File)) throw new ApiError('BAD_INPUT', 'Missing file.', 400);
    const kind = validateFile(file, undefined, maximum);
    if (isMockMode()) return responseJson(fixtureForType(kind).extraction);
    const body = new FormData();
    body.set('file', file);
    const result = await upstream('/api/extract', extractionSchema, {
      method: 'POST',
      body,
      signal: request.signal,
    });
    if (!result.text.trim() || result.text.trim().length < 10)
      throw new ApiError('EXTRACTION_EMPTY', 'No usable text.', 422);
    if (result.input_type !== kind)
      throw new ApiError('BAD_RESPONSE', 'Unexpected input type.', 502);
    return responseJson(result);
  });
}
