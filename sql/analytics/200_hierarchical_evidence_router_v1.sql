BEGIN;

CREATE TABLE IF NOT EXISTS analytics.evidence_compatibility_group_v1 (
    dimension_code text NOT NULL CHECK (dimension_code IN ('SESSION','REGIME')),
    raw_code text NOT NULL,
    compatible_group text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    rationale text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (dimension_code, raw_code)
);

INSERT INTO analytics.evidence_compatibility_group_v1(dimension_code,raw_code,compatible_group,rationale)
VALUES
 ('REGIME','TREND_UP_HIGH_VOL','TREND_HIGH_VOL','Одинаковая высокая волатильность; направление сохраняется на точном уровне'),
 ('REGIME','TREND_DOWN_HIGH_VOL','TREND_HIGH_VOL','Одинаковая высокая волатильность; направление сохраняется на точном уровне'),
 ('REGIME','RANGE_HIGH_VOL','RANGE_HIGH_VOL','Диапазон не объединяется с трендом'),
 ('REGIME','TREND_UP_NORMAL_VOL','TREND_NORMAL_VOL','Одинаковая нормальная волатильность'),
 ('REGIME','TREND_DOWN_NORMAL_VOL','TREND_NORMAL_VOL','Одинаковая нормальная волатильность'),
 ('REGIME','RANGE_NORMAL_VOL','RANGE_NORMAL_VOL','Диапазон не объединяется с трендом'),
 ('SESSION','MAIN','MAIN','Основная сессия'),
 ('SESSION','EVENING','EVENING','Вечерняя сессия отдельно'),
 ('SESSION','OFF_MAIN','OFF_MAIN','Вне основной сессии отдельно')
ON CONFLICT(dimension_code,raw_code) DO UPDATE SET
 compatible_group=excluded.compatible_group,rationale=excluded.rationale,
 enabled=true,updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.hierarchical_evidence_v1 (
    evidence_key text PRIMARY KEY,
    cohort_code text NOT NULL CHECK (cohort_code IN ('FRESH_V3_BASE','FRESH_V4_CONFIRM')),
    level_code text NOT NULL CHECK (level_code IN ('STRATEGY','INSTRUMENT_SIDE','COMPATIBLE_CONTEXT','EXACT_CONTEXT')),
    strategy_code text NOT NULL,
    symbol_code text NOT NULL DEFAULT '*',
    side_code text NOT NULL DEFAULT '*',
    session_code text NOT NULL DEFAULT '*',
    regime_code text NOT NULL DEFAULT '*',
    exit_rule text NOT NULL DEFAULT '*',
    closed_trades integer NOT NULL DEFAULT 0,
    target_trades integer NOT NULL DEFAULT 80 CHECK (target_trades=80),
    net_pnl numeric NOT NULL DEFAULT 0,
    expectancy numeric NOT NULL DEFAULT 0,
    profit_factor numeric NOT NULL DEFAULT 0,
    cost_ratio numeric NOT NULL DEFAULT 0,
    priority_score numeric NOT NULL DEFAULT 0,
    decision_code text NOT NULL CHECK (decision_code IN (
      'DISCOVERY_ONLY','COLLECT','EARLY_STOP','READY_FOR_OOS','NO_EVIDENCE'
    )),
    reason_code text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS hierarchical_evidence_priority_idx
 ON analytics.hierarchical_evidence_v1(decision_code,priority_score DESC,closed_trades DESC);

CREATE OR REPLACE VIEW analytics.hierarchical_oos_readiness_v1 AS
SELECT * FROM analytics.hierarchical_evidence_v1
WHERE cohort_code='FRESH_V4_CONFIRM' AND level_code='EXACT_CONTEXT';

CREATE OR REPLACE VIEW analytics.hierarchical_runtime_priority_v1 AS
SELECT DISTINCT ON (symbol_code) symbol_code AS symbol,priority_score,
       closed_trades AS accumulated_trades,false AS early_stopped,reason_code
FROM analytics.hierarchical_evidence_v1
WHERE symbol_code<>'*' AND decision_code IN ('COLLECT','DISCOVERY_ONLY','READY_FOR_OOS')
ORDER BY symbol_code,priority_score DESC,closed_trades DESC;

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version
) VALUES (
 'HIERARCHICAL_EVIDENCE_ROUTER','HIERARCHICAL_EVIDENCE_ROUTER_V1',true,
 'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',2,90,6,
 'HIERARCHICAL_EVIDENCE_ROUTER_V1'
) ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT ON analytics.evidence_compatibility_group_v1 TO alex,finam;
GRANT SELECT,INSERT,UPDATE,DELETE ON analytics.hierarchical_evidence_v1 TO alex,finam;
GRANT SELECT ON analytics.hierarchical_oos_readiness_v1 TO alex,finam;
GRANT SELECT ON analytics.hierarchical_runtime_priority_v1 TO alex,finam;

COMMIT;
