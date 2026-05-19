create table if not exists portfolio_execution_queue (
    id bigserial primary key,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    plan_id text not null,
    symbol text not null,

    priority integer not null,
    queue_state text not null default 'PLANNED',

    decision text not null,
    allocated_capital numeric not null default 0,
    allocated_qty numeric not null default 0,

    quality_score numeric,
    quality_grade text,
    expected_value numeric,

    reason text,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_portfolio_execution_queue_state
on portfolio_execution_queue(queue_state, priority, created_at desc);

create index if not exists idx_portfolio_execution_queue_symbol
on portfolio_execution_queue(symbol, created_at desc);

create unique index if not exists uq_portfolio_execution_queue_plan_symbol
on portfolio_execution_queue(plan_id, symbol);
