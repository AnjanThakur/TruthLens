-- Supabase pg_cron is required. Enable the pg_cron extension in the Dashboard first.
-- Run separately after the base migration, with the database owner's privileges.
create extension if not exists pg_cron;
select cron.schedule(
  'truthlens-delete-expired-reports', '17 * * * *',
  $$delete from public.verification_reports where retention_expires_at <= now()$$
);
