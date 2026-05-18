create table if not exists signal_alert_dedup (
    alert_key text primary key,
    symbol text not null,
    strategy text,
    regime text,
    decision text not null,
    last_sent_at timestamptz not null default now(),
    payload jsonb not null default '{}'::jsonb
);

create index if not exists idx_signal_alert_dedup_last_sent
on signal_alert_dedup(last_sent_at desc);
