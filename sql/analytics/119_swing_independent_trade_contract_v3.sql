BEGIN;

UPDATE analytics.swing_research_contract_v2
SET parameter_grid=jsonb_set(parameter_grid,'{allow_overlapping_positions}','[false]'::jsonb,true),
    pass_policy=pass_policy || '{"independent_trade_samples":true,"overlapping_positions":false}'::jsonb,
    config_version='V3_INDEPENDENT_TRADES',updated_at=clock_timestamp()
WHERE family_code IN ('REGIME_MOMENTUM','META_BREAKOUT');

UPDATE analytics.edge_search_scenario_v1
SET result_policy=result_policy || '{"independent_trade_samples":true,"overlapping_positions":false}'::jsonb,
    config_version='V3_INDEPENDENT_TRADES',updated_at=clock_timestamp()
WHERE scenario_code='SWING_EDGE_SEARCH';

UPDATE analytics.system_job_schedule_v1
SET config_version='V3_INDEPENDENT_TRADES',updated_at=clock_timestamp()
WHERE executor_code='SWING_EDGE_SEARCH_CYCLE_V1';

CREATE TABLE IF NOT EXISTS analytics.swing_validation_exclusion_v1 (
    validation_run_id uuid PRIMARY KEY,
    reason_code text NOT NULL,
    detail_ru text NOT NULL,
    promotion_allowed boolean NOT NULL DEFAULT false CHECK(NOT promotion_allowed),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.swing_validation_exclusion_v1(validation_run_id,reason_code,detail_ru)
SELECT validation_run_id,'OVERLAPPING_TRADE_SAMPLES',
       'Результат сохранён для аудита, но продвижение запрещено: сделки перекрывались во времени.'
FROM analytics.swing_selection_validation_result_v1
WHERE source_version='SWING_SELECTION_VALIDATION_ENGINE_V2_REGIME_META'
GROUP BY validation_run_id
ON CONFLICT(validation_run_id) DO NOTHING;

GRANT SELECT ON analytics.swing_validation_exclusion_v1 TO alex;

COMMIT;
