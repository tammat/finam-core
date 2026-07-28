BEGIN;

GRANT SELECT, INSERT ON analytics.research_archive_registry_v1 TO finam;

INSERT INTO analytics.research_archive_registry_v1(
    entity_type, entity_id, archive_reason, evidence, source_version
)
SELECT
    'TRADE_OUTCOME_HYPOTHESIS',
    h.hypothesis_id::text,
    CASE
        WHEN h.symbol = 'X' THEN 'INVALID_SYMBOL_X_REPLACED_BY_X5'
        WHEN h.lifecycle_state IN ('CLOSED', 'SUPERSEDED') THEN 'HYPOTHESIS_CLOSED'
        ELSE 'STALE_CONTRACT_REPLACED'
    END,
    jsonb_build_object(
        'symbol', h.symbol,
        'strategy_code', h.strategy_code,
        'lifecycle_state', h.lifecycle_state,
        'updated_at', h.updated_at
    ),
    'STALE_RESEARCH_BRANCH_ARCHIVE_V1'
FROM analytics.trade_outcome_hypothesis_v1 h
WHERE h.symbol = 'X'
   OR h.lifecycle_state IN ('CLOSED', 'SUPERSEDED')
   OR h.symbol IN ('BRM6','BRU6','NGN6')
ON CONFLICT(entity_type, entity_id) DO UPDATE SET
    archive_reason = EXCLUDED.archive_reason,
    evidence = EXCLUDED.evidence,
    archived_at = clock_timestamp(),
    source_version = EXCLUDED.source_version;

CREATE OR REPLACE VIEW analytics.trade_outcome_hypothesis_active_v4 AS
SELECT h.*
FROM analytics.trade_outcome_hypothesis_v1 h
WHERE NOT EXISTS (
    SELECT 1
    FROM analytics.research_archive_registry_v1 a
    WHERE a.entity_type = 'TRADE_OUTCOME_HYPOTHESIS'
      AND a.entity_id = h.hypothesis_id::text
);

COMMENT ON VIEW analytics.trade_outcome_hypothesis_active_v4 IS
    'Активные гипотезы без закрытых, ошибочных и заменённых контрактных веток; архивная статистика не удаляется.';

GRANT SELECT ON analytics.trade_outcome_hypothesis_active_v4,
    analytics.research_archive_summary_v1 TO alex, finam;

COMMIT;
