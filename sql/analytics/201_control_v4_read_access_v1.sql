BEGIN;

-- The operator UI connects as alex, while the V4 materializer owns the view as finam.
-- Keep the UI read-only and expose only the clean regime cohort.
GRANT USAGE ON SCHEMA analytics TO alex, finam;
GRANT SELECT ON analytics.closed_trades_fresh_v4_regime TO alex, finam;

COMMIT;
