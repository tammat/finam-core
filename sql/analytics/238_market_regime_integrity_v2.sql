BEGIN;

CREATE TABLE IF NOT EXISTS analytics.market_regime_cleanup_audit_v2(
 id bigserial PRIMARY KEY,cleaned_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 context_rows integer NOT NULL,variant_rows integer NOT NULL,reason text NOT NULL,
 source_version text NOT NULL);

INSERT INTO analytics.market_regime_cleanup_audit_v2(context_rows,variant_rows,reason,source_version)
SELECT (SELECT count(*) FROM analytics.market_regime_context_v1),
       (SELECT count(*) FROM analytics.market_regime_shadow_variant_v1),
       'V1 removed: non-causal RVI timestamp, stale physical MX M5 and non-V5 signals',
       'MARKET_REGIME_INTEGRITY_V2';

DELETE FROM analytics.market_regime_shadow_variant_v1;
DELETE FROM analytics.market_regime_context_v1;

ALTER TABLE analytics.market_regime_shadow_variant_v1
 ADD COLUMN IF NOT EXISTS entry_price numeric,
 ADD COLUMN IF NOT EXISTS stop_price numeric,
 ADD COLUMN IF NOT EXISTS take_price numeric,
 ADD COLUMN IF NOT EXISTS shadow_state text NOT NULL DEFAULT 'SKIPPED',
 ADD COLUMN IF NOT EXISTS exit_ts timestamptz,
 ADD COLUMN IF NOT EXISTS exit_price numeric,
 ADD COLUMN IF NOT EXISTS exit_reason text,
 ADD COLUMN IF NOT EXISTS gross_pnl numeric,
 ADD COLUMN IF NOT EXISTS execution_cost numeric,
 ADD COLUMN IF NOT EXISTS net_pnl numeric,
 ADD COLUMN IF NOT EXISTS closed_at timestamptz;

DO $$ BEGIN
 ALTER TABLE analytics.market_regime_shadow_variant_v1
  ADD CONSTRAINT market_regime_shadow_state_v2_check
  CHECK(shadow_state IN('OPEN','CLOSED','SKIPPED'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DROP VIEW IF EXISTS analytics.market_regime_variant_comparison_v1;
CREATE VIEW analytics.market_regime_variant_comparison_v1 AS
SELECT variant_code,count(*) observations,
 count(*) FILTER(WHERE decision_code='INCLUDE') included,
 count(*) FILTER(WHERE decision_code='SKIP') skipped,
 count(*) FILTER(WHERE shadow_state='OPEN') open_observations,
 count(*) FILTER(WHERE shadow_state='CLOSED') closed_observations,
 avg(risk_multiplier) average_risk_multiplier,
 sum(net_pnl) FILTER(WHERE shadow_state='CLOSED') net_pnl,
 avg(net_pnl) FILTER(WHERE shadow_state='CLOSED') expectancy,
 CASE WHEN abs(sum(net_pnl) FILTER(WHERE shadow_state='CLOSED' AND net_pnl<0))>0
      THEN sum(net_pnl) FILTER(WHERE shadow_state='CLOSED' AND net_pnl>0)
           /abs(sum(net_pnl) FILTER(WHERE shadow_state='CLOSED' AND net_pnl<0)) END profit_factor,
 max(signal_ts) latest_signal_at
FROM analytics.market_regime_shadow_variant_v1 GROUP BY variant_code;

UPDATE analytics.system_job_schedule_v1 SET priority=60,updated_at=clock_timestamp()
 WHERE job_code='RVI_REGIME_FEATURE';
UPDATE analytics.system_job_schedule_v1 SET executor_code='MARKET_REGIME_CONTEXT_V2',priority=61,
 config_version='MARKET_REGIME_CONTEXT_V2',updated_at=clock_timestamp()
 WHERE job_code='MARKET_REGIME_CONTEXT';
UPDATE analytics.system_job_schedule_v1 SET priority=62,updated_at=clock_timestamp()
 WHERE job_code='MX_INDEX_SHADOW_OBSERVER';

GRANT SELECT ON analytics.market_regime_cleanup_audit_v2 TO alex,finam;
GRANT USAGE,SELECT ON SEQUENCE analytics.market_regime_cleanup_audit_v2_id_seq TO alex,finam;
GRANT SELECT ON analytics.market_regime_variant_comparison_v1 TO alex,finam;

COMMIT;
