BEGIN;
ALTER TABLE analytics.profit_funnel_validated_edge_v2
    DROP CONSTRAINT IF EXISTS profit_funnel_validated_edge_v2_validation_status_check;
ALTER TABLE analytics.profit_funnel_validated_edge_v2
    ADD COLUMN IF NOT EXISTS validation_reason_code TEXT NOT NULL DEFAULT 'VALIDATED_EDGE_ELIGIBLE';
ALTER TABLE analytics.profit_funnel_validated_edge_v2
    ADD CONSTRAINT profit_funnel_validated_edge_v2_validation_status_check
    CHECK (validation_status IN ('PASS','REVOKED'));
GRANT UPDATE ON analytics.profit_funnel_validated_edge_v2 TO alex;
COMMIT;
