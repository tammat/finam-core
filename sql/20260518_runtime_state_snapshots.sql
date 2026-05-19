create table if not exists runtime_state_snapshots (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    state_key text not null,
    state_type text not null,

    active_signals integer not null default 0,
    active_watchlist integer not null default 0,
    active_positions integer not null default 0,

    status text not null default 'OK',
    reason text,

    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_runtime_state_snapshots_key
on runtime_state_snapshots(state_key, created_at desc);

create index if not exists idx_runtime_state_snapshots_type
on runtime_state_snapshots(state_type, created_at desc);
