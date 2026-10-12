export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status = 500,
  ) {
    super(message);
  }
}
export const errors: Record<string, string> = {
  ALERT_CONFLICT:
    'This candidate changed or expired. Refresh and review its current evidence before trying again.',
  MOCK_INPUT:
    'Synthetic mode only demonstrates the supplied examples. Restore the sample text, or connect the live backend to verify your own input.',
  BACKEND_OFFLINE: 'The verification service is unavailable. Please try again later.',
  NOT_CONFIGURED: 'The verification service has not been connected yet.',
  TIMEOUT: 'The service took too long. Your submission has not been saved. Please retry.',
  RATE_LIMIT: 'Too many requests. Please wait before trying again.',
  BAD_RESPONSE: 'The service returned an unsupported response. Please retry or contact the team.',
  BAD_INPUT: 'Please check your input and try again.',
  UPLOAD_TOO_LARGE: 'This file exceeds the upload limit.',
  UNSUPPORTED_FILE: 'This file format is not supported for the selected input.',
  EXTRACTION_EMPTY: 'No usable text was extracted. Try a clearer file or paste the text.',
  EXPLAIN_UNAVAILABLE:
    'A translated explanation is unavailable. The original cited result is shown.',
  HISTORY_DISABLED: 'Private history is not configured. You can still verify without signing in.',
  UNAUTHENTICATED: 'Sign in to access your private history.',
  CONSENT_REQUIRED: 'Choose to save this report before it can be stored.',
  MOCK_STORAGE: 'Synthetic reports cannot be saved to live history.',
  STORAGE_ERROR: 'History could not be updated. Please try again.',
  FORBIDDEN: 'This request is not allowed.',
};
export function errorMessage(code: string) {
  return errors[code] ?? 'Something went wrong. Please try again.';
}
