insert into market_event_calendar (
    event_time,
    event_type,
    instrument_group,
    event_name,
    severity,
    source,
    pre_event_block_min,
    pre_event_reduce_min,
    raw_json
)
values
(
    '2026-06-19 13:30:00+03',
    'CBR_RATE_DECISION',
    'USDRUB',
    'Заседание Банка России по ключевой ставке',
    'HIGH',
    'manual_cbr',
    120,
    1440,
    '{"source_url":"cbr.ru"}'::jsonb
),
(
    '2026-05-20 17:30:00+03',
    'EIA_INVENTORY',
    'BR',
    'EIA: еженедельные данные по запасам нефти',
    'HIGH',
    'manual_eia',
    30,
    90,
    '{"source_url":"eia.gov"}'::jsonb
)
on conflict do nothing;
