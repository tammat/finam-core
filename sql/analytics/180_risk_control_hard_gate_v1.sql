BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.risk_config_v2 (
    policy_key text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    max_portfolio_share numeric NOT NULL DEFAULT 0.60 CHECK (max_portfolio_share > 0 AND max_portfolio_share <= 1),
    elevated_reduction_factor numeric NOT NULL DEFAULT 0.50 CHECK (elevated_reduction_factor > 0 AND elevated_reduction_factor < 1),
    max_state_age_seconds integer NOT NULL DEFAULT 900 CHECK (max_state_age_seconds > 0),
    max_daily_loss_pct numeric NOT NULL DEFAULT 0.02 CHECK (max_daily_loss_pct > 0),
    max_drawdown_pct numeric NOT NULL DEFAULT 0.03 CHECK (max_drawdown_pct > 0),
    max_symbol_share numeric NOT NULL DEFAULT 0.10 CHECK (max_symbol_share > 0 AND max_symbol_share <= 1),
    max_gross_exposure_pct numeric NOT NULL DEFAULT 1.00 CHECK (max_gross_exposure_pct > 0),
    max_margin_utilization numeric NOT NULL DEFAULT 0.65 CHECK (max_margin_utilization > 0 AND max_margin_utilization <= 1),
    max_risk_per_trade_pct numeric NOT NULL DEFAULT 0.01 CHECK (max_risk_per_trade_pct > 0 AND max_risk_per_trade_pct <= 1),
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO analytics.risk_config_v2 (policy_key)
VALUES ('DEFAULT')
ON CONFLICT (policy_key) DO NOTHING;

ALTER TABLE analytics.risk_config_v2
    ADD COLUMN IF NOT EXISTS max_symbol_share numeric NOT NULL DEFAULT 0.10,
    ADD COLUMN IF NOT EXISTS max_gross_exposure_pct numeric NOT NULL DEFAULT 1.00,
    ADD COLUMN IF NOT EXISTS max_margin_utilization numeric NOT NULL DEFAULT 0.65,
    ADD COLUMN IF NOT EXISTS max_risk_per_trade_pct numeric NOT NULL DEFAULT 0.01;

CREATE TABLE IF NOT EXISTS analytics.risk_control_decision_v2 (
    decision_id uuid PRIMARY KEY,
    process_id uuid NOT NULL,
    symbol text NOT NULL,
    strategy_family text NOT NULL,
    decision_code text NOT NULL CHECK (decision_code IN ('ALLOW', 'REDUCE', 'BLOCK')),
    reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
    requested_quantity numeric NOT NULL DEFAULT 0,
    approved_quantity numeric NOT NULL DEFAULT 0,
    risk_budget_rub numeric,
    risk_per_contract_rub numeric,
    gross_exposure_rub numeric,
    symbol_exposure_rub numeric,
    used_margin_rub numeric,
    equity_rub numeric,
    peak_equity_rub numeric,
    entry_price numeric,
    stop_price numeric,
    contract_multiplier numeric,
    projected_cluster_share numeric,
    degradation_status text,
    daily_pnl_rub numeric,
    drawdown_rub numeric,
    spread_bps numeric,
    book_depth numeric,
    quote_observed_at timestamptz,
    policy_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE analytics.risk_control_decision_v2
    ADD COLUMN IF NOT EXISTS symbol_exposure_rub numeric,
    ADD COLUMN IF NOT EXISTS used_margin_rub numeric,
    ADD COLUMN IF NOT EXISTS equity_rub numeric,
    ADD COLUMN IF NOT EXISTS peak_equity_rub numeric,
    ADD COLUMN IF NOT EXISTS entry_price numeric,
    ADD COLUMN IF NOT EXISTS stop_price numeric,
    ADD COLUMN IF NOT EXISTS contract_multiplier numeric,
    ADD COLUMN IF NOT EXISTS projected_cluster_share numeric,
    ADD COLUMN IF NOT EXISTS degradation_status text;

CREATE INDEX IF NOT EXISTS idx_risk_control_decision_v2_process
    ON analytics.risk_control_decision_v2 (process_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_control_decision_v2_symbol
    ON analytics.risk_control_decision_v2 (symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_control_decision_v2_code
    ON analytics.risk_control_decision_v2 (decision_code, created_at DESC);

GRANT SELECT, INSERT, UPDATE ON analytics.risk_config_v2 TO alex, finam;
GRANT SELECT, INSERT ON analytics.risk_control_decision_v2 TO alex, finam;

COMMIT;
