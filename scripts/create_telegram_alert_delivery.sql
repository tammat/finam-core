create table if not exists telegram_alert_delivery (
    id bigserial primary key,
    alert_key text not null unique,
    delivered_at timestamptz not null default now(),
    payload jsonb not null default '{}'::jsonb
);
