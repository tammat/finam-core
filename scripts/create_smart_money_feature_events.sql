create table if not exists smart_money_feature_events (
    id bigserial primary key,
    ts timestamptz not null default now(),
    symbol text not null,

    rvol numeric not null,
    tick_velocity numeric not null,
    price_velocity numeric not null,
    range_pct numeric not null,

    absorption_score numeric not null,
    sweep_reclaim_score numeric not null,
    impulse_score numeric not null,
    smart_money_score numeric not null,
    label text not null,

    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_smart_money_feature_events_symbol_ts
on smart_money_feature_events(symbol, ts desc);

alter table market_opportunity_metrics
    add column if not exists smart_money_score numeric,
    add column if not exists smart_money_label text;
