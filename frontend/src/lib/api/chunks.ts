import type { Extraction } from './contracts';
export function extractionChunks(extraction: Extraction | null) {
  const chunks = extraction?.extraction_details.chunks;
  if (!Array.isArray(chunks)) return [];
  return chunks.filter(
    (value): value is { chunk_id: number; page_number?: number; text: string } =>
      value !== null &&
      typeof value === 'object' &&
      typeof value.text === 'string' &&
      typeof value.chunk_id === 'number',
  );
}
