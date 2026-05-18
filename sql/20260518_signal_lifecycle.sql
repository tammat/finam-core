create table if not exists signal_lifecycle (
    id bigserial primary key,
    signal_id text not null unique,

    symbol text not null,
    strategy text,
    regime text,

    state text not null default 'NEW',

    entry_price numeric,
    stop_loss numeric,
    take_profit numeric,
    risk_reward numeric,

    created_at timestamptz not null default now(),
    activated_at timestamptz,
    triggered_at timestamptz,
    closed_at timestamptz,
    expire_at timestamptz,

    close_reason text,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_signal_lifecycle_state
on signal_lifecycle(state, created_at desc);

create index if not exists idx_signal_lifecycle_symbol
on signal_lifecycle(symbol, created_at desc);
