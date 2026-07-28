BEGIN;

CREATE TABLE IF NOT EXISTS analytics.research_archive_registry_v1 (
    entity_type text NOT NULL,
    entity_id text NOT NULL,
    archive_reason text NOT NULL,
    evidence jsonb NOT NULL DEFAULT jsonb_build_object(),
    archived_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_version text NOT NULL DEFAULT 'RESEARCH_ARCHIVE_V1',
    PRIMARY KEY(entity_type, entity_id)
);

INSERT INTO analytics.research_archive_registry_v1(entity_type, entity_id, archive_reason, evidence)
SELECT
    'CLOSED_TRADE', id::text,
    CASE
        WHEN payload#>>'{context,cohort}' = 'LEGACY_DERIVED' THEN 'LEGACY_DERIVED'
        ELSE 'LEGACY_NO_CONTEXT'
    END,
    jsonb_build_object(
        'symbol', symbol,
        'closed_at', closed_at,
        'cohort', coalesce(payload#>>'{context,cohort}', 'NONE')
    )
FROM public.closed_trades
WHERE coalesce(payload#>>'{context,cohort}', 'NONE') IN ('NONE', 'LEGACY_DERIVED')
ON CONFLICT(entity_type, entity_id) DO NOTHING;

INSERT INTO analytics.research_archive_registry_v1(entity_type, entity_id, archive_reason, evidence)
SELECT
    'TRADE_OUTCOME_HYPOTHESIS', hypothesis_id::text,
    CASE
        WHEN symbol = 'X' THEN 'INVALID_SYMBOL_X_REPLACED_BY_X5'
        ELSE 'HYPOTHESIS_CLOSED'
    END,
    jsonb_build_object(
        'symbol', symbol,
        'strategy_code', strategy_code,
        'lifecycle_state', lifecycle_state
    )
FROM analytics.trade_outcome_hypothesis_v1
WHERE lifecycle_state IN ('CLOSED', 'SUPERSEDED') OR symbol = 'X'
ON CONFLICT(entity_type, entity_id) DO NOTHING;

INSERT INTO analytics.research_archive_registry_v1(entity_type, entity_id, archive_reason, evidence)
SELECT
    'OOS_FORWARD_HANDOFF', handoff_id::text,
    coalesce(reason_code, 'HANDOFF_REJECTED'),
    jsonb_build_object(
        'candidate_uuid', candidate_uuid,
        'observation_uuid', observation_uuid,
        'handoff_status', handoff_status
    )
FROM analytics.profit_funnel_oos_forward_handoff_v2
WHERE handoff_status = 'REJECTED'
ON CONFLICT(entity_type, entity_id) DO NOTHING;

CREATE OR REPLACE VIEW analytics.closed_trades_active_v3 AS
SELECT t.*
FROM public.closed_trades t
WHERE NOT EXISTS (
    SELECT 1
    FROM analytics.research_archive_registry_v1 a
    WHERE a.entity_type = 'CLOSED_TRADE'
      AND a.entity_id = t.id::text
);

CREATE OR REPLACE VIEW analytics.trade_outcome_hypothesis_active_v3 AS
SELECT h.*
FROM analytics.trade_outcome_hypothesis_v1 h
WHERE NOT EXISTS (
    SELECT 1
    FROM analytics.research_archive_registry_v1 a
    WHERE a.entity_type = 'TRADE_OUTCOME_HYPOTHESIS'
      AND a.entity_id = h.hypothesis_id::text
);

CREATE OR REPLACE VIEW analytics.research_archive_summary_v1 AS
SELECT entity_type, archive_reason, count(*)::bigint AS records, max(archived_at) AS archived_at
FROM analytics.research_archive_registry_v1
GROUP BY entity_type, archive_reason;

GRANT SELECT ON analytics.research_archive_registry_v1,
    analytics.closed_trades_active_v3,
    analytics.trade_outcome_hypothesis_active_v3,
    analytics.research_archive_summary_v1 TO alex;

COMMIT;
