create table if not exists runtime_active_universe (
    symbol text primary key,
    strategy text not null,
    regime text,
    score double precision not null default 0.0,
    priority integer not null default 0,
    is_enabled boolean not null default true,
    allocated_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    disabled_at timestamptz,
    disable_reason text,
    source text not null default 'runtime_universe_allocator',
    raw_json jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

create index if not exists idx_runtime_active_universe_enabled_priority
on runtime_active_universe(is_enabled, priority desc, score desc);

create index if not exists idx_runtime_active_universe_strategy
on runtime_active_universe(strategy, is_enabled);
