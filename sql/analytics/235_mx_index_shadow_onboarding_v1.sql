BEGIN;

INSERT INTO marketcore_ui.symbol_display_name_v1(symbol,display_name,asset_hint,source_version)
VALUES('MXU6@RTSX','Индекс МосБиржи, сентябрь 2026','Фьючерс','MX_INDEX_SHADOW_ONBOARDING_V1')
ON CONFLICT(symbol) DO UPDATE SET display_name=excluded.display_name,
 asset_hint=excluded.asset_hint,source_version=excluded.source_version,refreshed_at=clock_timestamp();

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES('MX_INDEX_SHADOW_OBSERVER','MX_INDEX_SHADOW_OBSERVER_V1',true,'Europe/Moscow',
 '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',5,120,67,
 'MX_INDEX_SHADOW_ONBOARDING_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 timezone_code=excluded.timezone_code,weekdays=excluded.weekdays,
 window_start=excluded.window_start,window_end=excluded.window_end,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

COMMENT ON TABLE analytics.system_job_schedule_v1 IS
'Governed scheduler; MXU6 is onboarded only as an IMOEX-derived Shadow/forward proxy. No Paper or REAL permission is granted.';

UPDATE analytics.system_job_schedule_v1 SET enabled=false,updated_at=clock_timestamp()
WHERE job_code='MX_FORWARD_PROXY_COHORT';

CREATE TABLE IF NOT EXISTS analytics.mx_index_shadow_signal_v1(
 id bigserial PRIMARY KEY,symbol text NOT NULL,timeframe text NOT NULL DEFAULT 'M5',
 signal_ts timestamptz NOT NULL,side text NOT NULL CHECK(side IN('LONG','SHORT')),
 entry_price numeric NOT NULL,stop_price numeric NOT NULL,take_price numeric NOT NULL,
 entry_reason text NOT NULL,rvi_regime text NOT NULL DEFAULT 'UNKNOWN',
 shadow_only boolean NOT NULL DEFAULT true,paper_allowed boolean NOT NULL DEFAULT false,
 live_allowed boolean NOT NULL DEFAULT false,source_version text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(symbol,timeframe,signal_ts,side));
GRANT SELECT,INSERT,UPDATE ON analytics.mx_index_shadow_signal_v1 TO alex,finam;
GRANT USAGE,SELECT ON SEQUENCE analytics.mx_index_shadow_signal_v1_id_seq TO alex,finam;

COMMIT;
