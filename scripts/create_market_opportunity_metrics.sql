create table if not exists market_opportunity_metrics (
    id bigserial primary key,

    symbol text not null,
    asset_class text not null default 'EQUITY',

    atr_pct numeric not null,
    rvol numeric not null,
    turnover numeric not null,
    spread_pct numeric not null,
    regime text not null,

    is_tradeable boolean not null default true,
    calculated_at timestamptz not null default now(),

    raw jsonb not null default '{}'::jsonb
);

create index if not exists idx_market_opportunity_metrics_latest
on market_opportunity_metrics(symbol, calculated_at desc);

create index if not exists idx_market_opportunity_metrics_tradeable
on market_opportunity_metrics(asset_class, is_tradeable, calculated_at desc);
