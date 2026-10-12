import type { InputType } from './contracts';
import { ApiError, errorMessage } from './errors';
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export const acceptedTypes = {
  image: ['image/jpeg', 'image/png'],
  audio: ['audio/mpeg', 'audio/ogg', 'audio/wav', 'audio/x-wav', 'video/ogg'],
  pdf: ['application/pdf'],
} as const;
export function fileKind(file: Pick<File, 'type'>): 'image' | 'audio' | 'pdf' | undefined {
  return (Object.keys(acceptedTypes) as ('image' | 'audio' | 'pdf')[]).find((kind) =>
    (acceptedTypes[kind] as readonly string[]).includes(file.type),
  );
}
export function validateFile(
  file: Pick<File, 'size' | 'type'>,
  kind?: InputType,
  maximum = MAX_UPLOAD_BYTES,
) {
  if (file.size === 0) throw new ApiError('BAD_INPUT', 'Choose a file containing data.', 400);
  if (file.size > maximum)
    throw new ApiError('UPLOAD_TOO_LARGE', errorMessage('UPLOAD_TOO_LARGE'), 413);
  const detected = fileKind(file);
  if (!detected || (kind && kind !== detected))
    throw new ApiError('UNSUPPORTED_FILE', errorMessage('UNSUPPORTED_FILE'), 415);
  return detected;
}
