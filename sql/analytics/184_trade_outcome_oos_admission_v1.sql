ALTER TABLE analytics.trade_outcome_hypothesis_v1
    ADD COLUMN IF NOT EXISTS symbol TEXT;

ALTER TABLE analytics.trade_outcome_hypothesis_v1
    DROP CONSTRAINT IF EXISTS trade_outcome_hypothesis_v1_hypothesis_type_check;
ALTER TABLE analytics.trade_outcome_hypothesis_v1
    ADD CONSTRAINT trade_outcome_hypothesis_v1_hypothesis_type_check
    CHECK (hypothesis_type IN (
        'FILTER_OOS_CANDIDATE','DATA_QUALITY_REMEDIATION',
        'LOSS_FILTER_REMEDIATION','SAMPLE_EXPANSION',
        'SESSION_FILTER_COHORT','EXIT_POLICY_REFINEMENT','REGIME_FILTER_COHORT',
        'INSTRUMENT_FILTER_COHORT'
    ));

CREATE TABLE IF NOT EXISTS analytics.paper_oos_strategy_map_v1 (
    paper_strategy_code TEXT PRIMARY KEY,
    oos_strategy_code TEXT NOT NULL REFERENCES analytics.strategy_library_v1(strategy_code),
    oos_timeframe TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    mapping_reason_ru TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.paper_oos_strategy_map_v1(
    paper_strategy_code,oos_strategy_code,oos_timeframe,mapping_reason_ru
) VALUES
    ('BR_CONSERVATIVE_BREAKOUT','VOLATILITY_BREAKOUT_V2','M5','Консервативный пробой BR проверяется как волатильностный пробой M5'),
    ('NG_CONSERVATIVE_BREAKOUT','VOLATILITY_BREAKOUT_V2','M5','Консервативный пробой NG проверяется как волатильностный пробой M5'),
    ('NG_CONSERVATIVE_BREAKOUT_M1','VOLATILITY_BREAKOUT_V2','M5','M1 не продвигается: проверяется безопасная M5-версия'),
    ('VWAP_BANDS_MR','VWAP_REVERSION_V1','M5','Полосы VWAP проверяются как возврат к VWAP M5')
ON CONFLICT(paper_strategy_code) DO UPDATE SET
    oos_strategy_code=excluded.oos_strategy_code,oos_timeframe=excluded.oos_timeframe,
    mapping_reason_ru=excluded.mapping_reason_ru,enabled=true,updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.trade_outcome_oos_admission_v1 (
    admission_id UUID PRIMARY KEY,
    hypothesis_id UUID NOT NULL UNIQUE REFERENCES analytics.trade_outcome_hypothesis_v1(hypothesis_id),
    symbol TEXT,
    fresh_closed_trades INTEGER NOT NULL DEFAULT 0,
    context_complete_trades INTEGER NOT NULL DEFAULT 0,
    microstructure_coverage_ratio NUMERIC NOT NULL DEFAULT 0 CHECK (microstructure_coverage_ratio BETWEEN 0 AND 1),
    required_microstructure_coverage NUMERIC NOT NULL DEFAULT 0.80 CHECK (required_microstructure_coverage BETWEEN 0 AND 1),
    status_code TEXT NOT NULL CHECK (status_code IN ('WAITING_HYPOTHESIS','WAITING_FRESH_DATA','WAITING_CONTEXT','WAITING_MICROSTRUCTURE','QUEUED','CLOSED')),
    reason_code TEXT NOT NULL,
    oos_request JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS trade_outcome_oos_admission_v1_status_idx
    ON analytics.trade_outcome_oos_admission_v1(status_code, updated_at DESC);

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
    interval_minutes,timeout_seconds,priority,config_version
) VALUES (
    'TRADE_OUTCOME_OOS_ADMISSION','TRADE_OUTCOME_OOS_ADMISSION_V1',true,
    'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',10,60,27,
    'TRADE_OUTCOME_OOS_ADMISSION_V1'
)
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=excluded.enabled,
    interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
    priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.trade_outcome_oos_admission_v1 TO alex;
