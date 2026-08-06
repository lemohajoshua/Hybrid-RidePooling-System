-- ================================================================
-- RidePool+ schema migration #3
-- Adds is_simulated flags so the Simulation Dashboard's "Initialize"
-- button can safely clear ONLY the synthetic data it generated, instead
-- of wiping every real registered driver/passenger in the database.
-- Also adds audit logging.
-- Run in Supabase SQL Editor. Safe to re-run.
-- ================================================================

create extension if not exists pgcrypto;

alter table drivers add column if not exists is_simulated boolean not null default false;
alter table passengers add column if not exists is_simulated boolean not null default false;
alter table ride_requests add column if not exists is_simulated boolean not null default false;
alter table delivery_tasks add column if not exists is_simulated boolean not null default false;

create index if not exists idx_drivers_simulated on drivers (is_simulated);
create index if not exists idx_passengers_simulated on passengers (is_simulated);
create index if not exists idx_ride_requests_simulated on ride_requests (is_simulated);
create index if not exists idx_delivery_tasks_simulated on delivery_tasks (is_simulated);

-- If you have ever clicked "Initialize" on the Simulation Dashboard before
-- applying this migration, your real test accounts (e.g. registered
-- drivers/passengers) may have been deleted by the old, unscoped version
-- of that endpoint. This migration only prevents it from happening again -
-- it can't recover anything already deleted. Re-register any accounts you
-- lost after applying this.

-- Audit logging (security requirement 3.6.3.v): a simple, queryable trail
-- of who did what and when, for monitoring and forensic analysis.
create table if not exists audit_log (
    log_id uuid primary key default gen_random_uuid(),
    user_id uuid,
    user_role text,
    action text not null,
    details jsonb,
    created_at timestamptz not null default now()
);
create index if not exists idx_audit_log_user on audit_log (user_id);
create index if not exists idx_audit_log_action on audit_log (action);
create index if not exists idx_audit_log_created on audit_log (created_at desc);

