import { spawn } from 'node:child_process';
const child = spawn(
  process.execPath,
  ['node_modules/next/dist/bin/next', 'dev', ...process.argv.slice(2)],
  {
    stdio: 'inherit',
    env: { ...process.env, USE_MOCK_API: 'true', NEXT_PUBLIC_USE_MOCK_API: 'true' },
  },
);
child.on('exit', (code) => process.exit(code ?? 1));
