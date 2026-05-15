create table if not exists strategy_runtime_regime_control (
    id bigserial primary key,
    symbol text not null,
    strategy text not null,
    regime text not null,
    status text not null,
    allow_trade boolean not null default false,
    watch_only boolean not null default true,
    risk_multiplier numeric not null default 0,
    reason text,
    updated_at timestamptz not null default now(),
    unique(symbol, strategy, regime)
);

create index if not exists idx_strategy_runtime_regime_control_lookup
on strategy_runtime_regime_control(symbol, strategy, regime);
