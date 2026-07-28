BEGIN;

CREATE TABLE IF NOT EXISTS analytics.archive_v3_oos_bridge_v1 (
    linkage_key text PRIMARY KEY,
    portfolio_scope text NOT NULL CHECK (portfolio_scope IN ('FRESH_V3_EQUITY','FRESH_V3_FUTURES')),
    symbol text NOT NULL,
    strategy_code text NOT NULL,
    side_code text NOT NULL,
    session_code text NOT NULL,
    regime_code text NOT NULL,
    exit_rule text NOT NULL,
    archive_hypothesis_id uuid REFERENCES analytics.trade_outcome_hypothesis_v1(hypothesis_id),
    archive_match_code text NOT NULL CHECK (archive_match_code IN ('EXACT','RELATED','V3_ONLY')),
    archive_priority numeric,
    archive_trades integer NOT NULL DEFAULT 0,
    archive_profit_factor numeric,
    v3_closed_trades integer NOT NULL DEFAULT 0,
    v3_context_complete integer NOT NULL DEFAULT 0,
    v3_profit_factor numeric NOT NULL DEFAULT 0,
    v3_expectancy numeric NOT NULL DEFAULT 0,
    target_trades integer NOT NULL DEFAULT 80,
    readiness_code text NOT NULL CHECK (readiness_code IN (
        'WAITING_SAMPLE','WAITING_CONTEXT','FAILED_FRESH_EVIDENCE','READY_FOR_OOS','QUEUED'
    )),
    reason_code text NOT NULL,
    oos_hypothesis_id uuid REFERENCES analytics.trade_outcome_hypothesis_v1(hypothesis_id),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS archive_v3_oos_bridge_readiness_idx
    ON analytics.archive_v3_oos_bridge_v1(readiness_code, v3_closed_trades DESC, updated_at DESC);

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
    interval_minutes,timeout_seconds,priority,config_version
) VALUES (
    'ARCHIVE_V3_OOS_BRIDGE','ARCHIVE_V3_OOS_BRIDGE_V1',true,
    'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',2,90,7,
    'ARCHIVE_V3_OOS_BRIDGE_V1'
)
ON CONFLICT(job_code) DO UPDATE SET
    executor_code=excluded.executor_code,enabled=excluded.enabled,
    interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
    priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.archive_v3_oos_bridge_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.archive_v3_oos_bridge_v1 TO finam;
GRANT SELECT ON analytics.trade_outcome_pattern_run_v1 TO alex;
GRANT SELECT ON analytics.trade_outcome_pattern_run_v1 TO finam;
GRANT SELECT ON analytics.closed_trades_active_v3 TO alex;
GRANT SELECT ON analytics.closed_trades_active_v3 TO finam;
GRANT SELECT,INSERT,UPDATE ON analytics.trade_outcome_hypothesis_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.trade_outcome_hypothesis_v1 TO finam;
GRANT SELECT,INSERT,UPDATE ON analytics.trade_outcome_oos_admission_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.trade_outcome_oos_admission_v1 TO finam;

COMMIT;
