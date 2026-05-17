create table if not exists runtime_universe_rotation_log (
    id bigserial primary key,
    symbol text not null,
    strategy text,
    regime text,
    previous_status text,
    new_status text not null,
    action text not null,
    score double precision,
    freshness_adjusted_score double precision,
    reason text,
    raw_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_runtime_universe_rotation_log_symbol_time
on runtime_universe_rotation_log(symbol, created_at desc);

create index if not exists idx_runtime_universe_rotation_log_action_time
on runtime_universe_rotation_log(action, created_at desc);
