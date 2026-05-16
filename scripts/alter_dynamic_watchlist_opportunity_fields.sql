alter table dynamic_watchlist
    add column if not exists strategy text,
    add column if not exists regime text,
    add column if not exists priority integer,
    add column if not exists is_active boolean not null default true,
    add column if not exists reason text,
    add column if not exists raw_json jsonb not null default '{}'::jsonb,
    add column if not exists updated_at timestamptz not null default now();

create index if not exists idx_dynamic_watchlist_strategy_active
on dynamic_watchlist(strategy, is_active, priority desc);
