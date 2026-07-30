BEGIN;

CREATE TABLE IF NOT EXISTS analytics.market_regime_context_v1(
 id bigserial PRIMARY KEY,context_ts timestamptz NOT NULL UNIQUE,mx_bar_ts timestamptz NOT NULL,
 mx_trend text NOT NULL CHECK(mx_trend IN('UP','DOWN','RANGE','UNKNOWN')),
 mx_strength numeric NOT NULL CHECK(mx_strength BETWEEN 0 AND 1),rvi_bar_ts timestamptz NOT NULL,
 rvi_value numeric NOT NULL,rvi_percentile numeric NOT NULL CHECK(rvi_percentile BETWEEN 0 AND 1),
 rvi_regime text NOT NULL CHECK(rvi_regime IN('LOW_VOL','NORMAL_VOL','HIGH_VOL')),
 rvi_direction text NOT NULL CHECK(rvi_direction IN('RISING','FALLING','FLAT')),
 market_regime text NOT NULL CHECK(market_regime IN('RISK_ON','RISK_OFF','RANGE','STRESS','HIGH_VOLATILITY')),
 source_version text NOT NULL,calculated_at timestamptz NOT NULL DEFAULT clock_timestamp());

CREATE TABLE IF NOT EXISTS analytics.market_regime_shadow_variant_v1(
 id bigserial PRIMARY KEY,parent_signal_id text NOT NULL,source_signal_pk bigint NOT NULL REFERENCES signals(id),
 symbol text NOT NULL,strategy text,side text NOT NULL,signal_ts timestamptz NOT NULL,
 variant_code text NOT NULL CHECK(variant_code IN('BASELINE','MX_FILTERED','MX_RVI_FILTERED')),
 decision_code text NOT NULL CHECK(decision_code IN('INCLUDE','SKIP')),
 risk_multiplier numeric NOT NULL CHECK(risk_multiplier BETWEEN 0 AND 1),reason_code text NOT NULL,
 context_ts timestamptz NOT NULL REFERENCES analytics.market_regime_context_v1(context_ts),
 market_context jsonb NOT NULL,source_version text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(parent_signal_id,variant_code));

CREATE OR REPLACE VIEW analytics.market_regime_variant_comparison_v1 AS
SELECT variant_code,count(*) observations,count(*) FILTER(WHERE decision_code='INCLUDE') included,
 count(*) FILTER(WHERE decision_code='SKIP') skipped,avg(risk_multiplier) average_risk_multiplier,
 max(signal_ts) latest_signal_at
FROM analytics.market_regime_shadow_variant_v1 GROUP BY variant_code;

INSERT INTO analytics.system_job_schedule_v1(job_code,executor_code,enabled,timezone_code,weekdays,
 window_start,window_end,interval_minutes,timeout_seconds,priority,config_version)
VALUES('MARKET_REGIME_CONTEXT','MARKET_REGIME_CONTEXT_V1',true,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,
 time '00:00',time '23:59',5,90,65,'MARKET_REGIME_CONTEXT_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.market_regime_context_v1,
 analytics.market_regime_shadow_variant_v1 TO alex,finam;
GRANT SELECT ON analytics.market_regime_variant_comparison_v1 TO alex,finam;
GRANT USAGE,SELECT ON SEQUENCE analytics.market_regime_context_v1_id_seq,
 analytics.market_regime_shadow_variant_v1_id_seq TO alex,finam;

COMMIT;
