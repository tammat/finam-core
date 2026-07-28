BEGIN;

UPDATE analytics.research_stream_v1
SET allocation_share = CASE stream_code
        WHEN 'FRESH_V3_EQUITY' THEN 0.60
        WHEN 'FRESH_V3_FUTURES' THEN 0.40
        WHEN 'FRESH_V3_BONDS' THEN 0.00
        ELSE allocation_share
    END,
    state_code = CASE
        WHEN stream_code = 'FRESH_V3_BONDS' THEN 'PAUSED_DATA_NOT_READY'
        ELSE state_code
    END,
    paper_enabled = CASE
        WHEN stream_code = 'FRESH_V3_BONDS' THEN false
        ELSE paper_enabled
    END,
    real_trading_enabled = false,
    updated_at = clock_timestamp()
WHERE stream_code IN ('FRESH_V3_EQUITY', 'FRESH_V3_FUTURES', 'FRESH_V3_BONDS');

UPDATE analytics.instrument_scout_policy_v1
SET policy = jsonb_set(
        jsonb_set(policy, '{category_quotas,BOND}', '0'::jsonb, true),
        '{bond_policy,next_state}',
        '"PAUSED_DATA_NOT_READY"'::jsonb,
        true
    )
WHERE policy_code = 'AUTONOMOUS_INSTRUMENT_SCOUT_V1';

INSERT INTO presentation.ui_resource_v1(
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, resource_group, source_version
) VALUES (
    'research.stream.state.paused_data_not_ready', 'ru',
    'Отложено: нет данных', 'Отложено', 'Отложено',
    'Исследование сохранено, но не расходует ресурсы до появления истории, спецификаций и ликвидности',
    'research', 'PAUSE_BOND_RESEARCH_V1'
)
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption = excluded.caption,
    caption_short = excluded.caption_short,
    caption_mobile = excluded.caption_mobile,
    tooltip = excluded.tooltip,
    source_version = excluded.source_version,
    updated_at = clock_timestamp();

COMMIT;
