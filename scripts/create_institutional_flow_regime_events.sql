create table if not exists institutional_flow_regime_events (
    id bigserial primary key,
    ts timestamptz not null default now(),
    symbol text not null,
    regime text not null,
    bias text not null,
    confidence numeric not null,
    reason text not null,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_institutional_flow_regime_events_symbol_ts
on institutional_flow_regime_events(symbol, ts desc);
