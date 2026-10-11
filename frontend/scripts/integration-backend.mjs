// Loopback-only fake P1 service for browser -> Next.js -> upstream acceptance.
// No provider SDKs, secrets, DNS fetches or real factual conclusions.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
const fixture = JSON.parse(
  await readFile(new URL('../tests/fixtures/person1-response.json', import.meta.url), 'utf8'),
);
const calls = [];
const send = (res, body, status = 200) => {
  res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(body));
};
const server = createServer(async (req, res) => {
  if (req.method === 'GET' && req.url === '/api/health')
    return send(res, { status: 'offline-integration-fixture', capabilities: { verify: true } });
  if (req.method === 'GET' && req.url === '/__test/calls') return send(res, calls);
  let raw = '';
  for await (const chunk of req) {
    raw += chunk.toString('latin1');
    if (raw.length > 11000000) return send(res, {}, 413);
  }
  if (req.url === '/api/extract') {
    const mime = raw.match(/Content-Type: ([^\r\n]+)/i)?.[1];
    const kind =
      mime === 'application/pdf' ? 'pdf' : mime?.startsWith('audio/') ? 'audio' : 'image';
    if (!raw.includes('name="file"')) return send(res, {}, 422);
    calls.push({ path: req.url, kind });
    return send(res, {
      text: 'A fictional extracted claim for offline integration.',
      input_type: kind,
      detected_language: 'en',
      warnings: [],
      extraction_details: {},
    });
  }
  let input;
  try {
    input = JSON.parse(Buffer.from(raw, 'latin1').toString('utf8'));
  } catch {
    return send(res, {}, 400);
  }
  if (req.url === '/api/extract/url') {
    calls.push({ path: req.url });
    return send(res, {
      text: 'A fictional article claim for offline integration.',
      input_type: 'url',
      detected_language: 'en',
      warnings: [],
      extraction_details: { content_complete: true },
    });
  }
  if (req.url === '/api/verify') {
    calls.push({ path: req.url, kind: input.input_type, language: input.response_language });
    if (input.text.includes('SIMULATE_UNAVAILABLE'))
      return send(res, { detail: 'private test diagnostic' }, 503);
    if (input.text.includes('SIMULATE_TIMEOUT')) return setTimeout(() => send(res, fixture), 2200);
    const result = structuredClone(fixture);
    result.input.text = input.text;
    result.input.input_type = input.input_type;
    result.response_language = input.response_language;
    result.audience = input.audience;
    result.status = 'partial';
    result.warnings = ['Offline integration: evidence retrieval intentionally incomplete.'];
    return send(res, result);
  }
  if (req.url === '/api/explain') {
    calls.push({ path: req.url, language: input.language });
    const result = structuredClone(input.result);
    result.response_language = input.language;
    result.audience = input.audience;
    result.summary = 'OFFLINE TRANSLATION FIXTURE — not a real fact-check.';
    return send(res, result);
  }
  return send(res, {}, 404);
});
server.listen(18101, '127.0.0.1', () =>
  console.log('Offline P1 fixture listening on loopback:18101'),
);
for (const signal of ['SIGINT', 'SIGTERM'])
  process.on(signal, () => server.close(() => process.exit(0)));
