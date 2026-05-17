alter table market_opportunity_metrics
    add column if not exists volatility_score double precision,
    add column if not exists rvol_score double precision,
    add column if not exists trend_efficiency_score double precision,
    add column if not exists liquidity_score_v2 double precision,
    add column if not exists spread_quality_score double precision,
    add column if not exists event_risk_penalty double precision,
    add column if not exists churn_penalty double precision,
    add column if not exists trade_priority_score double precision,
    add column if not exists trade_priority_label text,
    add column if not exists trade_priority_reason text;

create index if not exists idx_market_opportunity_trade_priority
on market_opportunity_metrics(trade_priority_score desc, calculated_at desc);
