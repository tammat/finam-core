BEGIN;

ALTER TABLE analytics.hierarchical_evidence_v1
    ADD COLUMN IF NOT EXISTS scope_code text NOT NULL DEFAULT '*',
    ADD COLUMN IF NOT EXISTS timeframe_code text NOT NULL DEFAULT '*';

COMMENT ON COLUMN analytics.hierarchical_evidence_v1.scope_code IS
'Изолированный portfolio scope; V5 equity и futures никогда не объединяются.';
COMMENT ON COLUMN analytics.hierarchical_evidence_v1.timeframe_code IS
'Таймфрейм входного evidence; разные горизонты не объединяются.';

CREATE INDEX IF NOT EXISTS hierarchical_evidence_v5_lookup_idx
ON analytics.hierarchical_evidence_v1(
    cohort_code,level_code,scope_code,timeframe_code,
    strategy_code,symbol_code,side_code
);

CREATE OR REPLACE VIEW analytics.hierarchical_oos_readiness_v1 AS
SELECT *
FROM analytics.hierarchical_evidence_v1
WHERE cohort_code='FRESH_V5_CONFIRM'
  AND level_code='EXACT_CONTEXT'
  AND decision_code='READY_FOR_OOS'
  AND closed_trades>=80
  AND profit_factor_observable
  AND expectancy>0
  AND profit_factor>=1.15;

GRANT SELECT,INSERT,UPDATE,DELETE ON analytics.hierarchical_evidence_v1 TO alex,finam;
GRANT SELECT ON analytics.hierarchical_oos_readiness_v1 TO alex,finam;

COMMIT;
