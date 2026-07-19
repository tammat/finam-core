BEGIN;

INSERT INTO analytics.market_session_research_contract_v1 (
    session_code,
    timezone_code,
    local_start,
    local_end,
    weekdays,
    priority,
    enabled,
    description_ru
) VALUES (
    'MOEX_WEEKEND',
    'Europe/Moscow',
    '10:00',
    '19:00',
    '[7]'::jsonb,
    60,
    true,
    'Воскресная сессия при подтверждённом живом потоке'
)
ON CONFLICT (session_code) DO UPDATE SET
    timezone_code = EXCLUDED.timezone_code,
    local_start = EXCLUDED.local_start,
    local_end = EXCLUDED.local_end,
    weekdays = EXCLUDED.weekdays,
    priority = EXCLUDED.priority,
    enabled = EXCLUDED.enabled,
    description_ru = EXCLUDED.description_ru;

COMMIT;
