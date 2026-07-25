-- ================================================================
-- RidePool+ schema migration #2
-- Adds: live ride-pooling groups, delivery driver assignment,
--       ratings/feedback, simple wallet-based payments.
-- Run in Supabase SQL Editor. Safe to re-run.
-- ================================================================

create extension if not exists pgcrypto;

-- 1. Ride-pooling: link two matched requests together
alter table ride_requests add column if not exists pool_group_id uuid;
create index if not exists idx_ride_requests_pool_group on ride_requests (pool_group_id);

-- 2. Delivery tasks: driver assignment + lifecycle timestamps
alter table delivery_tasks add column if not exists driver_id uuid references drivers(driver_id);
alter table delivery_tasks add column if not exists deadhead_score numeric;
alter table delivery_tasks add column if not exists assigned_at timestamptz;
alter table delivery_tasks add column if not exists picked_up_at timestamptz;
alter table delivery_tasks add column if not exists delivered_at timestamptz;
create index if not exists idx_delivery_tasks_driver_status on delivery_tasks (driver_id, status);

-- 3. Ratings / feedback (passenger <-> driver, either direction, one per trip per rater)
create table if not exists ratings (
    rating_id uuid primary key default gen_random_uuid(),
    request_id uuid not null,
    rater_role text not null check (rater_role in ('passenger', 'driver')),
    rater_id uuid not null,
    target_role text not null check (target_role in ('passenger', 'driver')),
    target_id uuid not null,
    stars int not null check (stars between 1 and 5),
    comment text,
    created_at timestamptz not null default now(),
    unique (request_id, rater_role)
);
create index if not exists idx_ratings_target on ratings (target_role, target_id);

-- 4. Simple in-app wallet / earnings (simulated payments, not a real payment gateway)
alter table passengers add column if not exists wallet_balance numeric not null default 5000;
alter table drivers add column if not exists total_earnings numeric not null default 0;
alter table drivers add column if not exists avg_rating numeric not null default 0;
alter table drivers add column if not exists rating_count int not null default 0;
alter table passengers add column if not exists avg_rating numeric not null default 0;
alter table passengers add column if not exists rating_count int not null default 0;

create table if not exists payments (
    payment_id uuid primary key default gen_random_uuid(),
    request_id uuid not null,
    passenger_id uuid not null references passengers(passenger_id),
    driver_id uuid not null references drivers(driver_id),
    amount numeric not null,
    status text not null default 'completed',
    created_at timestamptz not null default now()
);
create index if not exists idx_payments_passenger on payments (passenger_id);
create index if not exists idx_payments_driver on payments (driver_id);

-- 5. Ride requests: store the computed fare once so passenger/driver/payment agree on one number
alter table ride_requests add column if not exists fare numeric;
alter table ride_requests add column if not exists completed_at timestamptz;
