BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.runtime_entry_guard_policy_v1 (
    asset_group text PRIMARY KEY CHECK (asset_group IN ('EQUITY', 'FUTURES')),
    require_confirmed_regime boolean NOT NULL DEFAULT true,
    require_confirmed_volatility boolean NOT NULL DEFAULT true,
    require_expected_move boolean NOT NULL DEFAULT true,
    max_quote_age_seconds integer NOT NULL CHECK (max_quote_age_seconds > 0),
    max_spread_bps numeric NOT NULL CHECK (max_spread_bps > 0),
    high_volatility_size_multiplier numeric NOT NULL
        CHECK (high_volatility_size_multiplier > 0 AND high_volatility_size_multiplier <= 1),
    minimum_paper_trades integer NOT NULL CHECK (minimum_paper_trades >= 1),
    minimum_orderbook_coverage numeric NOT NULL
        CHECK (minimum_orderbook_coverage >= 0 AND minimum_orderbook_coverage <= 1),
    degradation_warning_ratio numeric NOT NULL
        CHECK (degradation_warning_ratio > 0 AND degradation_warning_ratio <= 1),
    degradation_block_ratio numeric NOT NULL
        CHECK (degradation_block_ratio > 0 AND degradation_block_ratio <= degradation_warning_ratio),
    enabled boolean NOT NULL DEFAULT true,
    reason text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE analytics.runtime_entry_guard_policy_v1 IS
'Единый DB-контракт входа и продвижения: подтверждённый режим, издержки, свежесть, стакан, выборка и деградация.';

INSERT INTO analytics.runtime_entry_guard_policy_v1(
    asset_group,
    require_confirmed_regime,
    require_confirmed_volatility,
    require_expected_move,
    max_quote_age_seconds,
    max_spread_bps,
    high_volatility_size_multiplier,
    minimum_paper_trades,
    minimum_orderbook_coverage,
    degradation_warning_ratio,
    degradation_block_ratio,
    reason
) VALUES
    ('EQUITY', true, true, true, 15, 35, 0.50, 80, 0.80, 0.80, 0.60,
     'Акции: подтверждённый режим и волатильность, реальный запас над издержками'),
    ('FUTURES', true, true, true, 8, 25, 0.50, 80, 0.80, 0.80, 0.60,
     'Фьючерсы: более строгая свежесть котировки и подтверждённый стакан')
ON CONFLICT(asset_group) DO UPDATE SET
    require_confirmed_regime=excluded.require_confirmed_regime,
    require_confirmed_volatility=excluded.require_confirmed_volatility,
    require_expected_move=excluded.require_expected_move,
    max_quote_age_seconds=excluded.max_quote_age_seconds,
    max_spread_bps=excluded.max_spread_bps,
    high_volatility_size_multiplier=excluded.high_volatility_size_multiplier,
    minimum_paper_trades=excluded.minimum_paper_trades,
    minimum_orderbook_coverage=excluded.minimum_orderbook_coverage,
    degradation_warning_ratio=excluded.degradation_warning_ratio,
    degradation_block_ratio=excluded.degradation_block_ratio,
    enabled=true,
    reason=excluded.reason,
    updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.runtime_entry_guard_audit_v1 (
    audit_id bigserial PRIMARY KEY,
    signal_id text,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    strategy_code text,
    regime_family text,
    side text,
    decision text NOT NULL CHECK (decision IN ('ALLOW', 'REDUCE', 'BLOCK')),
    reason_code text NOT NULL,
    expected_bps numeric,
    required_bps numeric,
    size_multiplier numeric NOT NULL DEFAULT 1,
    context jsonb NOT NULL DEFAULT '{}'::jsonb,
    decided_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_runtime_entry_guard_audit_v1_lookup
ON analytics.runtime_entry_guard_audit_v1(symbol, timeframe, decided_at DESC);

CREATE OR REPLACE VIEW analytics.runtime_policy_control_v1 AS
SELECT
    a.asset_group,
    a.require_confirmed_regime,
    a.require_confirmed_volatility,
    a.max_quote_age_seconds,
    a.max_spread_bps,
    a.minimum_paper_trades,
    a.minimum_orderbook_coverage,
    a.degradation_warning_ratio,
    a.degradation_block_ratio,
    count(*) FILTER (WHERE d.decision='ALLOW') AS allowed,
    count(*) FILTER (WHERE d.decision='REDUCE') AS reduced,
    count(*) FILTER (WHERE d.decision='BLOCK') AS blocked,
    max(d.decided_at) AS last_decision_at
FROM analytics.runtime_entry_guard_policy_v1 a
LEFT JOIN analytics.runtime_entry_guard_audit_v1 d
  ON CASE WHEN d.symbol LIKE '%@MISX' THEN 'EQUITY' ELSE 'FUTURES' END=a.asset_group
GROUP BY
    a.asset_group,
    a.require_confirmed_regime,
    a.require_confirmed_volatility,
    a.max_quote_age_seconds,
    a.max_spread_bps,
    a.minimum_paper_trades,
    a.minimum_orderbook_coverage,
    a.degradation_warning_ratio,
    a.degradation_block_ratio;

GRANT SELECT ON analytics.runtime_entry_guard_policy_v1 TO alex,finam;
GRANT SELECT,INSERT ON analytics.runtime_entry_guard_audit_v1 TO alex,finam;
GRANT USAGE,SELECT ON SEQUENCE analytics.runtime_entry_guard_audit_v1_audit_id_seq TO alex,finam;
GRANT SELECT ON analytics.runtime_policy_control_v1 TO alex,finam;

COMMIT;
