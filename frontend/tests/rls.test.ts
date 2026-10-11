// @vitest-environment node
import { PGlite } from '@electric-sql/pglite';
import { readFile } from 'node:fs/promises';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
const A = '00000000-0000-4000-8000-000000000001';
const B = '00000000-0000-4000-8000-000000000002';
let db: PGlite;
async function asUser(user: string) {
  await db.exec('reset role');
  await db.query("select set_config('request.jwt.claim.sub', $1, false)", [user]);
  await db.exec('set role authenticated');
}
async function insert(owner: string, verification = 'live-test', consent = true) {
  return db.query(
    `insert into public.verification_reports(owner_id, verification_id, input_type, input_excerpt, report_json, consent_to_store, retention_expires_at)
  values ($1, $2, 'text', 'Private test', $3, $4, now() + interval '7 days') returning id`,
    [
      owner,
      verification,
      JSON.stringify({
        verification_id: verification,
        status: 'completed',
        input: { input_type: 'text' },
      }),
      consent,
    ],
  );
}
beforeAll(async () => {
  db = new PGlite();
  await db.exec(`create role anon; create role authenticated;
    create schema auth; create table auth.users(id uuid primary key);
    create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
    grant usage on schema auth to anon, authenticated;
    grant execute on function auth.uid() to anon, authenticated;
    insert into auth.users values ('${A}'), ('${B}');`);
  await db.exec(
    await readFile(
      new URL('../../supabase/migrations/202610110001_private_reports.sql', import.meta.url),
      'utf8',
    ),
  );
}, 60000);
afterAll(async () => db?.close());
describe('actual PostgreSQL row-level security', () => {
  it('allows an authenticated owner to insert and read their report', async () => {
    await asUser(A);
    await insert(A);
    const rows = await db.query('select * from public.verification_reports');
    expect(rows.rows).toHaveLength(1);
  });
  it('hides another owner’s records and prevents cross-user writes/deletes', async () => {
    await asUser(B);
    expect((await db.query('select * from public.verification_reports')).rows).toHaveLength(0);
    expect(
      (await db.query('delete from public.verification_reports returning id')).rows,
    ).toHaveLength(0);
    await expect(insert(A, 'forged-owner')).rejects.toThrow();
    await insert(B, 'live-b');
    expect((await db.query('select * from public.verification_reports')).rows).toHaveLength(1);
  });
  it('rejects no-consent storage, synthetic IDs and snapshot updates', async () => {
    await asUser(A);
    await expect(insert(A, 'live-no-consent', false)).rejects.toThrow();
    await expect(insert(A, 'mock-illegal')).rejects.toThrow();
    await expect(
      db.exec("update public.verification_reports set input_excerpt='changed'"),
    ).rejects.toThrow();
  });
  it('denies unauthenticated reads and writes', async () => {
    await db.exec('reset role; set role anon');
    await expect(db.exec('select * from public.verification_reports')).rejects.toThrow();
    await expect(insert(A, 'anon-write')).rejects.toThrow();
  });
  it('hides expired records, allows owner hard deletion and permits scheduled purge', async () => {
    await db.exec('reset role');
    await db.exec(
      "update public.verification_reports set created_at=now()-interval '10 days', retention_expires_at=now()-interval '1 day' where verification_id='live-b'",
    );
    await asUser(B);
    expect((await db.query('select * from public.verification_reports')).rows).toHaveLength(0);
    await asUser(A);
    expect(
      (await db.query('delete from public.verification_reports returning id')).rows,
    ).toHaveLength(1);
    await db.exec('reset role');
    await db.exec('delete from public.verification_reports where retention_expires_at <= now()');
    expect((await db.query('select * from public.verification_reports')).rows).toHaveLength(0);
  });
});
