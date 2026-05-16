create table if not exists cross_contract_liquidity_decisions (
    id bigserial primary key,
    ts timestamptz not null default now(),
    continuous_symbol text not null,
    preferred_symbol text not null,
    score numeric not null,
    candidates text[] not null,
    reason text not null,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_cross_contract_liquidity_decisions_symbol_ts
on cross_contract_liquidity_decisions(continuous_symbol, ts desc);
