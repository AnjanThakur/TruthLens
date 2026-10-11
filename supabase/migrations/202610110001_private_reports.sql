begin;
create table public.verification_reports (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  verification_id text not null,
  input_type text not null check (input_type in ('text','image','audio','pdf','url')),
  input_excerpt text not null check (char_length(input_excerpt) <= 160),
  report_json jsonb not null check (jsonb_typeof(report_json) = 'object'),
  consent_to_store boolean not null check (consent_to_store = true),
  created_at timestamptz not null default now(),
  retention_expires_at timestamptz not null check (retention_expires_at > created_at and retention_expires_at <= created_at + interval '90 days'),
  unique(owner_id, verification_id),
  check (verification_id not like 'mock-%'),
  check (report_json ->> 'verification_id' = verification_id),
  check (report_json ->> 'status' = 'completed'),
  check (report_json -> 'input' ->> 'input_type' = input_type)
);
alter table public.verification_reports enable row level security;
alter table public.verification_reports force row level security;
revoke all on public.verification_reports from anon, authenticated;
grant select, insert, delete on public.verification_reports to authenticated;
create policy owner_read on public.verification_reports for select to authenticated
  using ((select auth.uid()) = owner_id and retention_expires_at > now());
create policy owner_insert on public.verification_reports for insert to authenticated
  with check ((select auth.uid()) = owner_id and consent_to_store = true and created_at <= now() and created_at >= now() - interval '1 minute');
create policy owner_delete on public.verification_reports for delete to authenticated
  using ((select auth.uid()) = owner_id);
create index reports_owner_id on public.verification_reports(owner_id, id desc);
create index reports_retention on public.verification_reports(retention_expires_at);
comment on table public.verification_reports is 'Explicitly saved private snapshots. No UPDATE grant; no public access. Expired rows hidden by RLS; scheduled hard purge required.';
commit;
