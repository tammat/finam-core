BEGIN;

ALTER TABLE analytics.market_regime_context_v1
 ADD COLUMN IF NOT EXISTS trend_probability numeric,
 ADD COLUMN IF NOT EXISTS range_probability numeric,
 ADD COLUMN IF NOT EXISTS shock_probability numeric,
 ADD COLUMN IF NOT EXISTS candidate_family text,
 ADD COLUMN IF NOT EXISTS stable_family text,
 ADD COLUMN IF NOT EXISTS pending_family text,
 ADD COLUMN IF NOT EXISTS pending_count integer NOT NULL DEFAULT 0,
 ADD COLUMN IF NOT EXISTS regime_switched boolean NOT NULL DEFAULT false,
 ADD COLUMN IF NOT EXISTS probability_source_version text;

DO $$ BEGIN
 ALTER TABLE analytics.market_regime_context_v1 ADD CONSTRAINT market_regime_probability_bounds_v1
 CHECK (
   trend_probability BETWEEN 0 AND 1 AND range_probability BETWEEN 0 AND 1
   AND shock_probability BETWEEN 0 AND 1
 );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
 ALTER TABLE analytics.market_regime_context_v1 ADD CONSTRAINT market_regime_family_v1
 CHECK (
   candidate_family IN ('TREND','RANGE','SHOCK')
   AND stable_family IN ('TREND','RANGE','SHOCK')
   AND (pending_family IS NULL OR pending_family IN ('TREND','RANGE','SHOCK'))
 );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

UPDATE analytics.system_job_schedule_v1
SET config_version='MARKET_REGIME_CONTEXT_V3',updated_at=clock_timestamp()
WHERE job_code='MARKET_REGIME_CONTEXT';

COMMIT;
