-- Recoverable quarantine for synthetic projections that have no fill/lifecycle evidence.
CREATE TABLE IF NOT EXISTS analytics.paper_projection_quarantine_v1 (
 portfolio_scope text NOT NULL,
 symbol text NOT NULL,
 original_state jsonb NOT NULL,
 original_updated_at timestamptz NOT NULL,
 reason_code text NOT NULL,
 quarantined_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(portfolio_scope,symbol)
);

INSERT INTO analytics.paper_projection_quarantine_v1(
 portfolio_scope,symbol,original_state,original_updated_at,reason_code)
SELECT p.portfolio_scope,p.symbol,p.state,p.updated_at,'SYNTHETIC_WITHOUT_FILL_OR_LIFECYCLE'
FROM analytics.paper_research_position_projection_v1 p
WHERE p.symbol='TEST@MISX'
  AND NOT EXISTS(SELECT 1 FROM signal_fills f WHERE f.portfolio_scope=p.portfolio_scope AND f.symbol=p.symbol)
  AND NOT EXISTS(SELECT 1 FROM analytics.paper_research_position_lifecycle_v1 l
                 WHERE l.portfolio_scope=p.portfolio_scope AND l.symbol=p.symbol)
ON CONFLICT DO NOTHING;

UPDATE analytics.paper_research_position_projection_v1 p
SET state=jsonb_set(jsonb_set(p.state,'{qty}','0'::jsonb),'{net_qty}','0'::jsonb),
    updated_at=clock_timestamp()
WHERE p.symbol='TEST@MISX'
  AND EXISTS(SELECT 1 FROM analytics.paper_projection_quarantine_v1 q
             WHERE q.portfolio_scope=p.portfolio_scope AND q.symbol=p.symbol);

CREATE TABLE IF NOT EXISTS analytics.market_shock_gate_replay_run_v1 (
 run_id uuid PRIMARY KEY,
 lookback_start timestamptz NOT NULL,
 lookback_end timestamptz NOT NULL,
 trades_evaluated integer NOT NULL,
 trades_blocked integer NOT NULL,
 losses_prevented_rub numeric NOT NULL,
 profits_foregone_rub numeric NOT NULL,
 net_protection_rub numeric NOT NULL,
 baseline_net_pnl_rub numeric NOT NULL,
 gated_net_pnl_rub numeric NOT NULL,
 result_json jsonb NOT NULL,
 generated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.monday_readiness_snapshot_v1 (
 snapshot_id bigserial PRIMARY KEY,
 evaluated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 session_phase text NOT NULL,
 event_code text,
 risk_level text NOT NULL,
 mx_last_ts timestamptz,
 rvi_last_ts timestamptz,
 mx_fresh boolean NOT NULL,
 rvi_fresh boolean NOT NULL,
 completed_mx_m15 integer NOT NULL,
 active_positions integer NOT NULL,
 oos_runs integer NOT NULL,
 verdict_code text NOT NULL,
 reason_code text NOT NULL,
 details jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- The scheduler executes as alex; the research refresh itself connects as finam.
GRANT INSERT,UPDATE ON analytics.trade_outcome_pattern_run_v1 TO finam;
GRANT SELECT,INSERT ON analytics.market_shock_gate_replay_run_v1 TO finam,alex;
GRANT SELECT,INSERT ON analytics.monday_readiness_snapshot_v1 TO finam,alex;
GRANT USAGE,SELECT ON SEQUENCE analytics.monday_readiness_snapshot_v1_snapshot_id_seq TO finam,alex;
GRANT SELECT ON analytics.paper_projection_quarantine_v1 TO finam,alex;

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES('MONDAY_READINESS','MONDAY_READINESS_V1',true,'Europe/Moscow','[0]'::jsonb,
       time '06:35',time '10:05',15,90,95,'MONDAY_READINESS_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,
 enabled=excluded.enabled,timezone_code=excluded.timezone_code,weekdays=excluded.weekdays,
 window_start=excluded.window_start,window_end=excluded.window_end,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();
