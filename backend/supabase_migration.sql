-- ================================================================
-- RidePool+ schema migration
-- Run this once in the Supabase SQL editor (Project → SQL Editor)
-- Safe to re-run: every statement is guarded with IF NOT EXISTS.
-- ================================================================

-- 1. Real password storage (auth currently checks nothing at all)
alter table passengers add column if not exists password_hash text;
alter table drivers    add column if not exists password_hash text;

-- 2. Separate "online/offline" toggle from the operational status
--    (status = idle/en-route/occupied/delivering/offline is what the
--     driver is doing right now; is_online = whether they want work at all)
alter table drivers add column if not exists is_online boolean not null default false;

-- 3. Ride requests: who it was offered to, whether it's a pooled request,
--    and when the driver responded
alter table ride_requests add column if not exists driver_id uuid references drivers(driver_id);
alter table ride_requests add column if not exists is_pooled boolean not null default false;
alter table ride_requests add column if not exists passenger_name text;
alter table ride_requests add column if not exists responded_at timestamptz;

-- Helpful indexes for the polling queries the app does
create index if not exists idx_ride_requests_driver_status on ride_requests (driver_id, status);
create index if not exists idx_ride_requests_passenger on ride_requests (passenger_id, request_time desc);
create index if not exists idx_drivers_online_status on drivers (is_online, status);
