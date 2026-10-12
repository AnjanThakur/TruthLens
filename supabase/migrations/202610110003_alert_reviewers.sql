-- Additive role allowlist. Does not alter Person 2's private report tables.
-- A project administrator must insert reviewers using the SQL editor/service role.
create table if not exists public.alert_reviewers (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  granted_at timestamptz not null default now()
);
alter table public.alert_reviewers enable row level security;
revoke all on public.alert_reviewers from anon, authenticated;
grant select on public.alert_reviewers to authenticated;
create policy "Reviewer may read own grant" on public.alert_reviewers
  for select to authenticated using (auth.uid() = owner_id);
