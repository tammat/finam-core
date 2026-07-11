CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.profit_factory_candidate_link_v1 (
    link_id BIGSERIAL PRIMARY KEY,
    candidate_id UUID NOT NULL REFERENCES analytics.profit_factory_candidate_identity_v1(candidate_id),
    target_stage TEXT NOT NULL,
    target_entity_type TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    link_method TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    confidence_score NUMERIC(10,6) NOT NULL DEFAULT 0,
    evidence_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_observed_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    verified_by TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_profit_factory_candidate_link_v1 UNIQUE (
        candidate_id, target_stage, target_entity_type, target_entity_id
    ),
    CONSTRAINT ck_profit_factory_link_stage_v1 CHECK (
        target_stage IN ('RESEARCH', 'EDGE', 'PAPER', 'RUNTIME', 'PRODUCTION')
    ),
    CONSTRAINT ck_profit_factory_link_method_v1 CHECK (
        link_method IN ('EXPLICIT_ID', 'SOURCE_REFERENCE', 'OPERATOR_APPROVED', 'INFERRED_MATCH')
    ),
    CONSTRAINT ck_profit_factory_link_verification_v1 CHECK (
        verification_status IN ('VERIFIED', 'PARTIAL', 'STALE', 'CONFLICT', 'UNVERIFIED', 'QUARANTINED')
    ),
    CONSTRAINT ck_profit_factory_link_confidence_v1 CHECK (
        confidence_score >= 0 AND confidence_score <= 1
    ),
    CONSTRAINT ck_profit_factory_link_verified_evidence_v1 CHECK (
        verification_status <> 'VERIFIED'
        OR (
            link_method IN ('EXPLICIT_ID', 'SOURCE_REFERENCE', 'OPERATOR_APPROVED')
            AND confidence_score = 1
            AND verified_at IS NOT NULL
            AND verified_by IS NOT NULL
            AND btrim(verified_by) <> ''
        )
    ),
    CONSTRAINT ck_profit_factory_link_inferred_v1 CHECK (
        link_method <> 'INFERRED_MATCH'
        OR verification_status IN ('UNVERIFIED', 'QUARANTINED')
    )
);

CREATE INDEX IF NOT EXISTS ix_profit_factory_link_candidate_stage_v1
ON analytics.profit_factory_candidate_link_v1(candidate_id, target_stage);

CREATE INDEX IF NOT EXISTS ix_profit_factory_link_quality_v1
ON analytics.profit_factory_candidate_link_v1(verification_status);

CREATE OR REPLACE VIEW analytics.profit_factory_trust_status_v1 AS
WITH link_quality AS (
    SELECT
        candidate_id,
        count(*) AS link_count,
        count(*) FILTER (WHERE verification_status='VERIFIED') AS verified_link_count,
        count(*) FILTER (WHERE verification_status='CONFLICT') AS conflict_link_count,
        count(*) FILTER (WHERE verification_status='QUARANTINED') AS quarantined_link_count,
        count(*) FILTER (
            WHERE verification_status='STALE'
               OR (expires_at IS NOT NULL AND expires_at <= now())
        ) AS stale_link_count,
        count(*) FILTER (
            WHERE target_stage='PAPER' AND verification_status='VERIFIED'
        ) AS verified_paper_count,
        count(*) FILTER (
            WHERE target_stage='RUNTIME' AND verification_status='VERIFIED'
        ) AS verified_runtime_count,
        count(*) FILTER (
            WHERE target_stage='PRODUCTION' AND verification_status='VERIFIED'
        ) AS verified_production_count,
        max(updated_at) AS last_evidence_at
    FROM analytics.profit_factory_candidate_link_v1
    GROUP BY candidate_id
)
SELECT
    i.candidate_id,
    i.edge_candidate_id,
    i.research_batch_id,
    i.strategy_code,
    i.strategy_version,
    i.symbol,
    i.timeframe,
    i.parameter_hash,
    i.dataset_version,
    COALESCE(q.link_count, 0) AS link_count,
    COALESCE(q.verified_link_count, 0) AS verified_link_count,
    CASE
        WHEN COALESCE(q.conflict_link_count, 0) > 0 THEN 'CONFLICT'
        WHEN COALESCE(q.quarantined_link_count, 0) > 0 THEN 'QUARANTINED'
        WHEN COALESCE(q.stale_link_count, 0) > 0 THEN 'STALE'
        WHEN COALESCE(q.link_count, 0) = 0 THEN 'UNVERIFIED'
        WHEN COALESCE(q.verified_link_count, 0) < COALESCE(q.link_count, 0) THEN 'PARTIAL'
        WHEN COALESCE(q.verified_paper_count, 0) = 0 THEN 'PARTIAL'
        WHEN COALESCE(q.verified_runtime_count, 0) = 0 THEN 'PARTIAL'
        WHEN COALESCE(q.verified_production_count, 0) = 0 THEN 'PARTIAL'
        ELSE 'VERIFIED'
    END AS data_quality_status,
    (
        COALESCE(q.conflict_link_count, 0) = 0
        AND COALESCE(q.quarantined_link_count, 0) = 0
        AND COALESCE(q.stale_link_count, 0) = 0
        AND COALESCE(q.verified_paper_count, 0) > 0
        AND COALESCE(q.verified_runtime_count, 0) > 0
        AND COALESCE(q.verified_production_count, 0) > 0
    ) AS financial_kpi_eligible,
    CASE
        WHEN COALESCE(q.conflict_link_count, 0) > 0 THEN 'INVESTIGATE_CONFLICT'
        WHEN COALESCE(q.quarantined_link_count, 0) > 0 THEN 'REVIEW_QUARANTINE'
        WHEN COALESCE(q.stale_link_count, 0) > 0 THEN 'REFRESH_EVIDENCE'
        WHEN COALESCE(q.link_count, 0) = 0 THEN 'PROVIDE_EXPLICIT_LINKS'
        WHEN COALESCE(q.verified_paper_count, 0) = 0 THEN 'VERIFY_PAPER_LINK'
        WHEN COALESCE(q.verified_runtime_count, 0) = 0 THEN 'VERIFY_RUNTIME_LINK'
        WHEN COALESCE(q.verified_production_count, 0) = 0 THEN 'VERIFY_PRODUCTION_LINK'
        ELSE 'READY_FOR_FINANCIAL_KPI'
    END AS next_trust_action,
    q.last_evidence_at,
    now() AS assessed_at,
    i.data_scope
FROM analytics.profit_factory_candidate_identity_v1 i
LEFT JOIN link_quality q ON q.candidate_id=i.candidate_id;

CREATE OR REPLACE VIEW analytics.profit_factory_trust_summary_v1 AS
SELECT
    count(*) AS total_candidates,
    count(*) FILTER (WHERE data_quality_status='VERIFIED') AS verified_candidates,
    count(*) FILTER (WHERE data_quality_status='PARTIAL') AS partial_candidates,
    count(*) FILTER (WHERE data_quality_status='STALE') AS stale_candidates,
    count(*) FILTER (WHERE data_quality_status='CONFLICT') AS conflict_candidates,
    count(*) FILTER (WHERE data_quality_status='UNVERIFIED') AS unverified_candidates,
    count(*) FILTER (WHERE data_quality_status='QUARANTINED') AS quarantined_candidates,
    count(*) FILTER (WHERE financial_kpi_eligible) AS financial_kpi_eligible_candidates,
    now() AS assessed_at
FROM analytics.profit_factory_trust_status_v1
WHERE data_scope='REAL';

COMMENT ON TABLE analytics.profit_factory_candidate_link_v1 IS
'Evidence registry. Inferred matches can never be VERIFIED or enter financial KPIs.';

GRANT SELECT, INSERT, UPDATE ON analytics.profit_factory_candidate_link_v1 TO alex;
GRANT USAGE, SELECT ON SEQUENCE analytics.profit_factory_candidate_link_v1_link_id_seq TO alex;
GRANT SELECT ON analytics.profit_factory_trust_status_v1 TO alex;
GRANT SELECT ON analytics.profit_factory_trust_summary_v1 TO alex;
