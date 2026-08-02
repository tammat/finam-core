BEGIN;

CREATE TABLE IF NOT EXISTS analytics.adaptive_regime_paper_pilot_v1 (
    pilot_id UUID PRIMARY KEY,
    shadow_candidate_id UUID NOT NULL UNIQUE,
    symbol TEXT NOT NULL,
    side_code TEXT NOT NULL CHECK (side_code IN ('LONG','SHORT')),
    strategy_code TEXT NOT NULL,
    regime_code TEXT NOT NULL,
    candidate_code TEXT NOT NULL,
    entry_mode TEXT NOT NULL,
    stop_atr NUMERIC NOT NULL,
    take_atr NUMERIC NOT NULL,
    status_code TEXT NOT NULL CHECK (
        status_code IN ('SHADOW_COLLECTING','PILOT_ACTIVE','PAPER_CONFIRMED','ROLLED_BACK')
    ),
    shadow_observations INTEGER NOT NULL DEFAULT 0,
    shadow_profit_factor NUMERIC,
    shadow_expectancy NUMERIC,
    shadow_max_drawdown NUMERIC,
    paper_observations INTEGER NOT NULL DEFAULT 0,
    paper_profit_factor NUMERIC,
    paper_expectancy NUMERIC,
    rollback_reason TEXT,
    max_open_positions INTEGER NOT NULL DEFAULT 1,
    max_pilot_trades INTEGER NOT NULL DEFAULT 5,
    activated_at TIMESTAMPTZ,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS adaptive_regime_paper_pilot_lookup_v1
ON analytics.adaptive_regime_paper_pilot_v1(symbol,side_code,strategy_code,status_code);

GRANT SELECT,INSERT,UPDATE ON analytics.adaptive_regime_paper_pilot_v1 TO alex;

ALTER TABLE analytics.adaptive_regime_paper_pilot_v1
    ADD COLUMN IF NOT EXISTS entry_mode TEXT,
    ADD COLUMN IF NOT EXISTS stop_atr NUMERIC,
    ADD COLUMN IF NOT EXISTS take_atr NUMERIC;

COMMIT;

DO $$
BEGIN
INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
    interval_minutes,timeout_seconds,priority,config_version,updated_at
) VALUES (
    'ADAPTIVE_REGIME_PILOT','ADAPTIVE_REGIME_PILOT_V1',TRUE,
    'Europe/Moscow','[0,1,2,3,4]'::jsonb,'06:40','23:59',
    5,120,25,'V1_SEQUENTIAL_REGIME_PILOT',clock_timestamp()
) ON CONFLICT(job_code) DO UPDATE SET
    executor_code=EXCLUDED.executor_code,enabled=TRUE,
    interval_minutes=EXCLUDED.interval_minutes,timeout_seconds=EXCLUDED.timeout_seconds,
    config_version=EXCLUDED.config_version,updated_at=clock_timestamp();
EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'system schedule unchanged: owner migration required';
END $$;

DO $$
BEGIN
    GRANT INSERT,UPDATE ON analytics.entry_exit_runtime_profile_v1 TO finam;
    GRANT USAGE,SELECT ON SEQUENCE
      analytics.entry_exit_runtime_profile_v1_profile_id_seq TO finam;
EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'runtime profile grant unchanged: owner migration required';
END $$;

DO $$
BEGIN
INSERT INTO analytics.edge_search_scenario_step_v1(
    scenario_code,step_order,executor_code,title_ru,enabled,timeout_seconds,required
)
SELECT 'AUTONOMOUS_EDGE_SEARCH',
       coalesce((SELECT max(step_order)+1 FROM analytics.edge_search_scenario_step_v1
                 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH'),1),
       'EVALUATE_ADAPTIVE_PILOT','Адаптивная оценка Shadow и Paper-пилота',
       TRUE,120,TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM analytics.edge_search_scenario_step_v1
    WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH'
      AND executor_code='EVALUATE_ADAPTIVE_PILOT'
);
EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'scenario step unchanged: owner migration required';
END $$;
