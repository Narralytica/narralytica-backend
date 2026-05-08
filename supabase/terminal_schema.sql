create extension if not exists pgcrypto;

create table if not exists public.terminal_payloads (
  payload_key text primary key,
  payload jsonb not null,
  version text,
  generated_at timestamptz,
  published_at timestamptz not null default now(),
  source text not null,
  refresh_interval_minutes integer not null,
  payload_hash text,
  updated_at timestamptz not null default now()
);

create index if not exists terminal_payloads_generated_at_idx
  on public.terminal_payloads (generated_at desc);

alter table public.terminal_payloads enable row level security;

drop policy if exists "public can read terminal payloads" on public.terminal_payloads;
create policy "public can read terminal payloads"
  on public.terminal_payloads
  for select
  to anon, authenticated
  using (true);

drop policy if exists "service role manages terminal payloads" on public.terminal_payloads;
create policy "service role manages terminal payloads"
  on public.terminal_payloads
  for all
  to service_role
  using (true)
  with check (true);
