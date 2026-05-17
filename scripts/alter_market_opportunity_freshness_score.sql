alter table market_opportunity_metrics
    add column if not exists signal_age_min double precision,
    add column if not exists freshness_score double precision,
    add column if not exists freshness_adjusted_score double precision,
    add column if not exists freshness_reason text;

create index if not exists idx_market_opportunity_freshness_score
on market_opportunity_metrics(freshness_adjusted_score desc, calculated_at desc);
