BEGIN;
ALTER TABLE analytics.market_regime_context_v1
 ADD COLUMN IF NOT EXISTS rvi_fresh boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN analytics.market_regime_context_v1.rvi_fresh IS
 'True only when the causal RVI observation is no more than 30 minutes old at context_ts';
COMMIT;
