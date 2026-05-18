create table if not exists radar_candidate_analysis (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    source text not null default 'market_radar',

    decision text not null,
    reason text,

    strategy text,
    regime text,

    entry_price numeric,
    stop_loss numeric,
    take_profit numeric,
    risk_reward numeric,
    score numeric,

    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_radar_candidate_analysis_symbol
on radar_candidate_analysis(symbol, created_at desc);

create index if not exists idx_radar_candidate_analysis_decision
on radar_candidate_analysis(decision, created_at desc);
