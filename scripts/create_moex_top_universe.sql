create table if not exists moex_top_universe (
    id bigserial primary key,
    symbol text not null,
    board text,
    asset_class text not null default 'EQUITY',
    short_name text,
    last_price double precision,
    change_pct double precision,
    value_today double precision,
    volume_today double precision,
    intraday_range_pct double precision,
    turnover_score double precision,
    volatility_score double precision,
    volume_score double precision,
    total_score double precision,
    reason text,
    source text not null default 'moex_top_universe',
    calculated_at timestamptz not null default now()
);

create index if not exists idx_moex_top_universe_latest
on moex_top_universe(calculated_at desc);

create index if not exists idx_moex_top_universe_score
on moex_top_universe(total_score desc, calculated_at desc);

create index if not exists idx_moex_top_universe_symbol
on moex_top_universe(symbol, calculated_at desc);
