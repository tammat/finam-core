BEGIN;

CREATE TABLE IF NOT EXISTS analytics.edge_strict_rule_policy_v2(
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    lookback_days integer NOT NULL CHECK(lookback_days BETWEEN 7 AND 730),
    min_closed_trades integer NOT NULL CHECK(min_closed_trades BETWEEN 5 AND 10000),
    min_expectancy_after_costs numeric NOT NULL DEFAULT 0,
    reload_seconds integer NOT NULL CHECK(reload_seconds BETWEEN 5 AND 3600),
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.edge_strict_rule_policy_v2(
    policy_code,lookback_days,min_closed_trades,min_expectancy_after_costs,
    reload_seconds,config_version)
VALUES('DEFAULT',180,30,0,60,'EDGE_STRICT_RULE_V2')
ON CONFLICT(policy_code) DO UPDATE SET
    enabled=true,
    lookback_days=excluded.lookback_days,
    min_closed_trades=excluded.min_closed_trades,
    min_expectancy_after_costs=excluded.min_expectancy_after_costs,
    reload_seconds=excluded.reload_seconds,
    config_version=excluded.config_version,
    updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.edge_strict_rule_v2(
    normalized_symbol text NOT NULL,
    strategy text NOT NULL,
    entry_side text NOT NULL CHECK(entry_side IN ('BUY','SELL')),
    session_name text NOT NULL,
    closed_trades integer NOT NULL CHECK(closed_trades >= 0),
    wins integer NOT NULL CHECK(wins >= 0),
    losses integer NOT NULL CHECK(losses >= 0),
    pnl_points numeric NOT NULL,
    expectancy_points numeric NOT NULL,
    pnl_after_costs numeric NOT NULL,
    expectancy_after_costs numeric NOT NULL,
    rule_action text NOT NULL CHECK(rule_action IN ('ALLOW','BLOCK','INSUFFICIENT_DATA')),
    enabled boolean NOT NULL DEFAULT true,
    evidence_started_at timestamptz,
    evidence_finished_at timestamptz,
    built_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    source_code text NOT NULL DEFAULT 'PAPER_CLOSED_TRADES_V2',
    PRIMARY KEY(normalized_symbol,strategy,entry_side,session_name)
);

CREATE INDEX IF NOT EXISTS edge_strict_rule_v2_action_idx
ON analytics.edge_strict_rule_v2(rule_action,normalized_symbol,strategy);

CREATE TABLE IF NOT EXISTS analytics.edge_strict_rule_build_run_v2(
    build_run_id uuid PRIMARY KEY,
    status_code text NOT NULL CHECK(status_code IN ('RUNNING','COMPLETE','FAILED')),
    rules_total integer NOT NULL DEFAULT 0,
    allow_total integer NOT NULL DEFAULT 0,
    block_total integer NOT NULL DEFAULT 0,
    insufficient_total integer NOT NULL DEFAULT 0,
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    error_text text
);

GRANT SELECT ON analytics.edge_strict_rule_policy_v2 TO alex,finam;
GRANT SELECT ON analytics.edge_strict_rule_v2 TO alex,finam;
GRANT SELECT ON analytics.edge_strict_rule_build_run_v2 TO alex,finam;
GRANT INSERT,UPDATE,DELETE ON analytics.edge_strict_rule_v2 TO alex,finam;
GRANT INSERT,UPDATE ON analytics.edge_strict_rule_build_run_v2 TO alex,finam;

COMMIT;
BEGIN;

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,
    window_start,window_end,priority,timeout_seconds,config_version)
VALUES(
    'EDGE_STRICT_RULE_BUILD','EDGE_STRICT_RULE_BUILD_V2',true,5,'Europe/Moscow',
    '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',4,50,'EDGE_STRICT_RULE_V2'
)
ON CONFLICT(job_code) DO UPDATE SET
    executor_code=excluded.executor_code,
    enabled=true,
    interval_minutes=excluded.interval_minutes,
    timezone_code=excluded.timezone_code,
    weekdays=excluded.weekdays,
    window_start=excluded.window_start,
    window_end=excluded.window_end,
    priority=excluded.priority,
    timeout_seconds=excluded.timeout_seconds,
    config_version=excluded.config_version,
    updated_at=clock_timestamp();

COMMIT;
