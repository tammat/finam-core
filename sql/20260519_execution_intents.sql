create table if not exists execution_intents (
    id bigserial primary key,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    queue_id bigint,
    symbol text not null,

    intent_state text not null default 'READY',

    side text not null default 'BUY',

    planned_qty numeric not null default 0,
    executed_qty numeric not null default 0,
    remaining_qty numeric not null default 0,

    planned_price numeric,
    avg_execution_price numeric,

    execution_priority integer not null default 0,

    broker_order_id text,

    execution_mode text not null default 'paper',

    retry_count integer not null default 0,

    reason text,

    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_execution_intents_state
on execution_intents(intent_state, execution_priority, created_at desc);

create index if not exists idx_execution_intents_symbol
on execution_intents(symbol, created_at desc);

create unique index if not exists uq_execution_intents_queue
on execution_intents(queue_id);
