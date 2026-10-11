import { spawn } from 'node:child_process';
const child = spawn(
  process.execPath,
  ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', '3101'],
  {
    stdio: 'inherit',
    env: {
      ...process.env,
      BACKEND_BASE_URL: 'http://127.0.0.1:18101',
      BACKEND_API_TOKEN: '',
      BACKEND_TIMEOUT_MS: '1500',
      MAX_UPLOAD_BYTES: '1048576',
      APP_ORIGIN: 'http://127.0.0.1:3101',
      USE_MOCK_API: 'false',
      NEXT_PUBLIC_USE_MOCK_API: 'false',
      NEXT_PUBLIC_SUPABASE_URL: '',
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: '',
      HISTORY_SIGNING_SECRET: '',
    },
  },
);
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('exit', (code) => process.exit(code ?? 1));
