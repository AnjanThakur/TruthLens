-- Read-only owner preflight in the Supabase SQL editor. No grants or mutations.
select to_regclass('public.verification_reports') as history_table,
       to_regclass('public.alert_reviewers') as reviewer_table,
       to_regclass('cron.job') as cron_table;

select tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename in ('verification_reports', 'alert_reviewers');

select c.relname, c.relrowsecurity, c.relforcerowsecurity
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in ('verification_reports', 'alert_reviewers');

select name,
       case when to_regclass('public.' || name) is not null
         then has_table_privilege('authenticated', 'public.' || name, 'SELECT') end
         as authenticated_select,
       case when to_regclass('public.' || name) is not null
         then has_table_privilege('anon', 'public.' || name, 'SELECT') end
         as anonymous_select
from (values ('verification_reports'), ('alert_reviewers')) as tables(name);

-- Run these separately ONLY if cron_table above is non-null.
-- select jobname, schedule, active, command from cron.job
-- where jobname = 'truthlens-delete-expired-reports';
-- select status, start_time, end_time from cron.job_run_details
-- where jobid in (select jobid from cron.job
--                where jobname = 'truthlens-delete-expired-reports')
-- order by start_time desc limit 3;

-- To check your own reviewer grant, replace the placeholder with your existing
-- Auth user UUID locally in the SQL editor; do not share tokens or credentials.
-- select exists(select 1 from public.alert_reviewers
--               where owner_id = '<your-existing-auth-user-uuid>'::uuid);
