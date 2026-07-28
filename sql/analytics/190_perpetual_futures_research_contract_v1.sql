BEGIN;

UPDATE analytics.instrument_scout_policy_v1
SET policy = jsonb_set(
        policy,
        '{perpetual_symbols}',
        jsonb_build_array('USDRUBF@RTSX', 'CNYRUBF@RTSX'),
        true
    )
WHERE policy_code = 'AUTONOMOUS_INSTRUMENT_SCOUT_V1';

UPDATE analytics.research_stream_v1
SET policy = jsonb_set(
        policy,
        '{perpetual_symbols}',
        jsonb_build_array('USDRUBF@RTSX', 'CNYRUBF@RTSX'),
        true
    ),
    updated_at = clock_timestamp()
WHERE stream_code = 'FRESH_V3_FUTURES';

INSERT INTO presentation.ui_resource_v1(
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, resource_group, source_version
) VALUES
    ('research.contract.perpetual', 'ru', 'Вечный фьючерс', 'Вечный', 'Вечный',
     'Контракт без квартального rollover; проверяется по собственной непрерывной истории',
     'research', 'PERPETUAL_FUTURES_CONTRACT_V1')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption = excluded.caption,
    caption_short = excluded.caption_short,
    caption_mobile = excluded.caption_mobile,
    tooltip = excluded.tooltip,
    source_version = excluded.source_version,
    updated_at = clock_timestamp();

COMMIT;
