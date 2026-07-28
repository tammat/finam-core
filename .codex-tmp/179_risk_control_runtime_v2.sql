-- Единый риск-контур Paper: политика, аудит каждого допуска и исполнение без
-- неявного фиксированного плеча.  Реальная торговля этим объектом не включается.
CREATE TABLE IF NOT EXISTS analytics.risk_control_decision_v2 (
    decision_id UUID PRIMARY KEY,
    process_id UUID NOT NULL,
    symbol TEXT NOT NULL,
    strategy_family TEXT NOT NULL,
    decision_code TEXT NOT NULL CHECK (decision_code IN ('ALLOW','REDUCE','BLOCK')),
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    requested_quantity NUMERIC NOT NULL DEFAULT 0,
    approved_quantity NUMERIC NOT NULL DEFAULT 0,
    risk_budget_rub NUMERIC NOT NULL DEFAULT 0,
    risk_per_contract_rub NUMERIC NOT NULL DEFAULT 0,
    gross_exposure_rub NUMERIC NOT NULL DEFAULT 0,
    daily_pnl_rub NUMERIC NOT NULL DEFAULT 0,
    drawdown_rub NUMERIC NOT NULL DEFAULT 0,
    spread_bps NUMERIC,
    book_depth NUMERIC,
    quote_observed_at TIMESTAMPTZ,
    policy_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS risk_control_decision_v2_process_created_idx
    ON analytics.risk_control_decision_v2(process_id, created_at DESC);
CREATE INDEX IF NOT EXISTS risk_control_decision_v2_symbol_created_idx
    ON analytics.risk_control_decision_v2(symbol, created_at DESC);

UPDATE analytics.swing_paper_risk_policy_v1
SET policy = policy || '{
  "max_risk_per_trade_share": 0.01,
  "default_stop_loss_bps": 80,
  "max_spread_bps": 25,
  "min_book_depth": 1,
  "max_quote_age_seconds": 30,
  "max_positions_per_cluster": 1,
  "degradation_min_closed_trades": 10,
  "degradation_max_loss_streak": 3
}'::jsonb,
source_version='RISK_CONTROL_RUNTIME_V2'
WHERE active;

GRANT SELECT, INSERT ON analytics.risk_control_decision_v2 TO alex;
