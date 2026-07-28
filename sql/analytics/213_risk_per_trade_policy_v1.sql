BEGIN;

ALTER TABLE analytics.risk_config_v2
    ADD COLUMN IF NOT EXISTS max_risk_per_trade_pct numeric NOT NULL DEFAULT 0.01;

ALTER TABLE analytics.risk_config_v2
    DROP CONSTRAINT IF EXISTS risk_config_v2_max_risk_per_trade_pct_check;

ALTER TABLE analytics.risk_config_v2
    ADD CONSTRAINT risk_config_v2_max_risk_per_trade_pct_check
    CHECK (max_risk_per_trade_pct > 0 AND max_risk_per_trade_pct <= 1);

COMMENT ON COLUMN analytics.risk_config_v2.max_risk_per_trade_pct IS
    'Maximum loss at the protective stop as a fraction of portfolio equity; 0.01 means 1%.';

GRANT SELECT, INSERT, UPDATE ON analytics.risk_config_v2 TO alex, finam;

COMMIT;
