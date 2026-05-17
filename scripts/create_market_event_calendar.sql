create table if not exists market_event_calendar (
    id bigserial primary key,
    event_time timestamptz not null,
    event_type text not null,
    instrument_group text not null,
    event_name text not null,
    severity text not null default 'MEDIUM',
    source text not null default 'manual',
    pre_event_block_min integer not null default 30,
    pre_event_reduce_min integer not null default 90,
    is_active boolean not null default true,
    raw_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_market_event_calendar_active_time
on market_event_calendar(is_active, event_time);

create index if not exists idx_market_event_calendar_group_time
on market_event_calendar(instrument_group, event_time);
