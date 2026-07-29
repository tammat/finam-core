BEGIN;

CREATE TABLE IF NOT EXISTS analytics.v5_futures_rollover_state_v1(
 root_symbol text PRIMARY KEY CHECK(root_symbol IN ('BR','NG','GD')),
 current_symbol text NOT NULL,
 scope_code text NOT NULL REFERENCES analytics.paper_portfolio_scope_v1(scope_code),
 enabled boolean NOT NULL DEFAULT true,
 last_rolled_at timestamptz,
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.v5_futures_rollover_state_v1(root_symbol,current_symbol,scope_code) VALUES
 ('BR','BRQ6@RTSX','FRESH_V5_CONFIRMED_FUTURES'),
 ('NG','NGQ6@RTSX','FRESH_V5_CONFIRMED_FUTURES'),
 ('GD','GDU6@RTSX','FRESH_V5_GOLD_FUTURES')
ON CONFLICT(root_symbol) DO UPDATE SET scope_code=excluded.scope_code,enabled=true,
updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.v5_futures_rollover_decision_v1(
 decision_id bigserial PRIMARY KEY,
 root_symbol text NOT NULL,
 current_symbol text NOT NULL,
 next_symbol text,
 action_code text NOT NULL CHECK(action_code IN ('KEEP','BLOCK','DRY_RUN','SWITCH','ERROR')),
 reason_code text NOT NULL,
 details jsonb NOT NULL DEFAULT '{}'::jsonb,
 decided_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS v5_futures_rollover_decision_latest_v1
 ON analytics.v5_futures_rollover_decision_v1(root_symbol,decided_at DESC);

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version
) VALUES(
 'V5_FUTURES_FLAT_LIQUIDITY_ROLLOVER','V5_FUTURES_FLAT_LIQUIDITY_ROLLOVER_V1',true,
 'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',5,90,6,
 'V5_FUTURES_FLAT_LIQUIDITY_ROLLOVER_V1'
) ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,
 enabled=true,interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

-- Next contracts collect bars before activation. They are watch-only here and do
-- not enter runtime_active_universe until the flat/liquidity rollover transaction.
INSERT INTO market_data_watch_universe(symbol,asset_group,timeframe,is_enabled,reason,updated_at)
SELECT symbol,asset_group,'M1',true,'V5 rollover candidate prewarm',clock_timestamp()
FROM (VALUES
 ('BRU6@RTSX','BR'),('NGU6@RTSX','GAS'),('GDZ6@RTSX','GOLD')
) candidate(symbol,asset_group)
ON CONFLICT(symbol) DO UPDATE SET is_enabled=true,
 reason=excluded.reason,updated_at=excluded.updated_at;

GRANT SELECT,INSERT,UPDATE ON analytics.v5_futures_rollover_state_v1,
 analytics.v5_futures_rollover_decision_v1 TO alex,finam;
GRANT USAGE,SELECT ON SEQUENCE analytics.v5_futures_rollover_decision_v1_decision_id_seq TO alex,finam;

COMMIT;
