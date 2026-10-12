// @vitest-environment node
import { PGlite } from '@electric-sql/pglite';
import { readFile } from 'node:fs/promises';
import { expect, it } from 'vitest';
it('reviewer allowlist cannot be self-granted, altered or read across users', async () => {
  const db = new PGlite();
  const a = '00000000-0000-4000-8000-000000000001';
  const b = '00000000-0000-4000-8000-000000000002';
  try {
    await db.exec(
      `create role anon; create role authenticated; create schema auth; create table auth.users(id uuid primary key); create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$; grant usage on schema auth to authenticated; grant execute on function auth.uid() to authenticated; insert into auth.users values ('${a}'),('${b}');`,
    );
    await db.exec(
      await readFile(
        new URL('../../supabase/migrations/202610110003_alert_reviewers.sql', import.meta.url),
        'utf8',
      ),
    );
    await db.exec(
      `insert into public.alert_reviewers(owner_id) values ('${a}'); select set_config('request.jwt.claim.sub','${a}',false); set role authenticated;`,
    );
    expect((await db.query('select owner_id from public.alert_reviewers')).rows).toHaveLength(1);
    await expect(
      db.exec(`insert into public.alert_reviewers(owner_id) values ('${b}')`),
    ).rejects.toThrow();
    await expect(db.exec('delete from public.alert_reviewers')).rejects.toThrow();
    await expect(db.exec('update public.alert_reviewers set granted_at=now()')).rejects.toThrow();
    await db.exec(
      `reset role; select set_config('request.jwt.claim.sub','${b}',false); set role authenticated;`,
    );
    expect((await db.query('select owner_id from public.alert_reviewers')).rows).toHaveLength(0);
    await db.exec('reset role; set role anon;');
    await expect(db.exec('select * from public.alert_reviewers')).rejects.toThrow();
  } finally {
    await db.close();
  }
}, 60000);
