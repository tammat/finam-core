BEGIN;

-- DB-квоты заменяют локальный счётчик процесса. Ключ квоты всегда включает
-- режим, канонический инструмент, стратегию и рыночный режим.
CREATE TABLE IF NOT EXISTS analytics.paper_research_quota_policy_v1 (
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    execution_mode text NOT NULL,
    normalized_symbol text NOT NULL,
    strategy text NOT NULL,
    regime_code text NOT NULL DEFAULT 'ANY',
    window_seconds integer NOT NULL CHECK (window_seconds BETWEEN 60 AND 86400),
    max_fills integer NOT NULL CHECK (max_fills BETWEEN 1 AND 1000),
    reservation_ttl_seconds integer NOT NULL DEFAULT 180
        CHECK (reservation_ttl_seconds BETWEEN 30 AND 3600),
    priority integer NOT NULL DEFAULT 100,
    reserved_research_slots boolean NOT NULL DEFAULT false,
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.paper_research_quota_reservation_v1 (
    reservation_id uuid PRIMARY KEY,
    execution_mode text NOT NULL,
    normalized_symbol text NOT NULL,
    strategy text NOT NULL,
    regime_code text NOT NULL,
    policy_code text NOT NULL REFERENCES analytics.paper_research_quota_policy_v1(policy_code),
    status_code text NOT NULL CHECK (status_code IN ('RESERVED','FILLED','EXPIRED','CANCELLED')),
    reserved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz NOT NULL,
    filled_at timestamptz,
    source_process text NOT NULL DEFAULT 'paper_pipeline',
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS paper_research_quota_active_v1
ON analytics.paper_research_quota_reservation_v1(
    execution_mode,normalized_symbol,strategy,regime_code,reserved_at DESC
) WHERE status_code IN ('RESERVED','FILLED');

INSERT INTO analytics.paper_research_quota_policy_v1(
    policy_code,execution_mode,normalized_symbol,strategy,regime_code,
    window_seconds,max_fills,reservation_ttl_seconds,priority,
    reserved_research_slots,config_version
) VALUES
('BR_RESEARCH_PAPER','PAPER','BR_CONT','BR_CONSERVATIVE_BREAKOUT','ANY',3600,6,180,1,true,'DB_QUOTA_V1'),
('DEFAULT_RESEARCH_PAPER','PAPER','*','*','ANY',3600,2,180,100,false,'DB_QUOTA_V1')
ON CONFLICT(policy_code) DO UPDATE SET
    enabled=true,execution_mode=excluded.execution_mode,
    normalized_symbol=excluded.normalized_symbol,strategy=excluded.strategy,
    regime_code=excluded.regime_code,window_seconds=excluded.window_seconds,
    max_fills=excluded.max_fills,reservation_ttl_seconds=excluded.reservation_ttl_seconds,
    priority=excluded.priority,reserved_research_slots=excluded.reserved_research_slots,
    config_version=excluded.config_version,updated_at=clock_timestamp();

-- Новая когорта начинается с момента установки миграции. Исторические строки
-- с неполным стаканом в неё не переносятся.
CREATE TABLE IF NOT EXISTS analytics.microstructure_clean_cohort_policy_v4 (
    cohort_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    normalized_symbol text NOT NULL,
    cohort_started_at timestamptz NOT NULL,
    min_coverage_ratio numeric NOT NULL CHECK(min_coverage_ratio BETWEEN 0 AND 1),
    min_matched_trades integer NOT NULL CHECK(min_matched_trades > 0),
    required_bid_ask boolean NOT NULL DEFAULT true,
    required_depth boolean NOT NULL DEFAULT true,
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.microstructure_clean_cohort_policy_v4(
    cohort_code,normalized_symbol,cohort_started_at,min_coverage_ratio,
    min_matched_trades,config_version
) VALUES ('BR_CLEAN_BOOK_V4','BR_CONT',clock_timestamp(),0.80,30,'CLEAN_BOOK_COHORT_V4')
ON CONFLICT(cohort_code) DO UPDATE SET
    enabled=true,min_coverage_ratio=0.80,min_matched_trades=30,
    config_version=excluded.config_version,updated_at=clock_timestamp();

ALTER TABLE analytics.execution_edge_result_v1
    DROP CONSTRAINT IF EXISTS execution_edge_result_v1_cohort_code_check;
ALTER TABLE analytics.execution_edge_result_v1
    ADD CONSTRAINT execution_edge_result_v1_cohort_code_check
    CHECK(cohort_code IN ('HISTORICAL_BAR_ONLY','MICROSTRUCTURE_ONLY','MICROSTRUCTURE_CLEAN_V4'));

ALTER TABLE analytics.execution_edge_result_v1
    DROP CONSTRAINT IF EXISTS execution_edge_result_v1_market_data_quality_check;
ALTER TABLE analytics.execution_edge_result_v1
    ADD CONSTRAINT execution_edge_result_v1_market_data_quality_check
    CHECK(market_data_quality IN ('BAR_ONLY','QUOTE_VERIFIED','MICROSTRUCTURE_VERIFIED',
                                  'QUOTE_MATCHED','MICROSTRUCTURE_COHORT_VERIFIED'));

ALTER TABLE analytics.edge_strict_rule_policy_v2
    ADD COLUMN IF NOT EXISTS min_microstructure_coverage numeric NOT NULL DEFAULT 0.80;

ALTER TABLE analytics.edge_strict_rule_v2
    ADD COLUMN IF NOT EXISTS timeframe text NOT NULL DEFAULT 'M5';
ALTER TABLE analytics.edge_strict_rule_v2
    ADD COLUMN IF NOT EXISTS regime_code text NOT NULL DEFAULT 'UNKNOWN';
ALTER TABLE analytics.edge_strict_rule_v2
    ADD COLUMN IF NOT EXISTS microstructure_coverage_ratio numeric NOT NULL DEFAULT 0;
ALTER TABLE analytics.edge_strict_rule_v2
    ADD COLUMN IF NOT EXISTS evidence_cohort_code text NOT NULL DEFAULT 'UNVERIFIED';

DO $$
DECLARE constraint_name text;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid='analytics.edge_strict_rule_v2'::regclass AND contype='p'
    LIMIT 1;
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE analytics.edge_strict_rule_v2 DROP CONSTRAINT %I',constraint_name);
    END IF;
END $$;

ALTER TABLE analytics.edge_strict_rule_v2
    ADD PRIMARY KEY(normalized_symbol,strategy,timeframe,entry_side,session_name,regime_code);

ALTER TABLE analytics.walkforward_campaign_v4
    DROP CONSTRAINT IF EXISTS walkforward_campaign_v4_phase_code_check;
ALTER TABLE analytics.walkforward_campaign_v4
    ADD CONSTRAINT walkforward_campaign_v4_phase_code_check
    CHECK(phase_code IN ('COARSE','FULL_OOS','HOLDOUT','COMPLETE'));
ALTER TABLE analytics.walkforward_variant_task_v4
    DROP CONSTRAINT IF EXISTS walkforward_variant_task_v4_phase_code_check;
ALTER TABLE analytics.walkforward_variant_task_v4
    ADD CONSTRAINT walkforward_variant_task_v4_phase_code_check
    CHECK(phase_code IN ('COARSE','FULL_OOS','HOLDOUT','REJECTED'));

-- Восстановление M15 выполняется идемпотентно из трёх завершённых M5-свечей.
INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
    interval_minutes,timeout_seconds,priority,config_version
) VALUES(
    'M15_REBUILD_FROM_M5_V1','M15_REBUILD_FROM_M5_V1',true,'Europe/Moscow',
    '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',5,120,3,'M15_FROM_M5_V1'
)
ON CONFLICT(job_code) DO UPDATE SET
    executor_code=excluded.executor_code,enabled=true,interval_minutes=excluded.interval_minutes,
    timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,
    config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT ON analytics.paper_research_quota_policy_v1 TO alex,finam;
GRANT SELECT,INSERT,UPDATE ON analytics.paper_research_quota_reservation_v1 TO alex,finam;
GRANT SELECT ON analytics.microstructure_clean_cohort_policy_v4 TO alex,finam;

COMMIT;
