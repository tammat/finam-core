BEGIN;

-- Execution enforcement lives in paper_pipeline.  This migration normalizes
-- the already existing control limits without changing owner-managed schema.
UPDATE analytics.adaptive_regime_paper_pilot_v1
SET max_open_positions=1,
    max_pilot_trades=least(max_pilot_trades,5)
WHERE source_version IN ('ADAPTIVE_REGIME_PILOT_V1','ADAPTIVE_REGIME_PILOT_V2');

COMMIT;
