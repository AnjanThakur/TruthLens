// P1's default request deadline is 180 seconds. Leave time for transport and
// schema validation, then let the browser outlive the website's proxy deadline.
export const DEFAULT_BACKEND_TIMEOUT_MS = 195000;
export const CLIENT_TIMEOUT_MS = 330000;

export function backendTimeout(value: string | undefined) {
  if (value === undefined || value === '') return DEFAULT_BACKEND_TIMEOUT_MS;
  const timeout = Number(value);
  return Number.isInteger(timeout) && timeout >= 1000 && timeout <= 300000 ? timeout : null;
}
