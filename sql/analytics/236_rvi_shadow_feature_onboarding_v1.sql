BEGIN;

INSERT INTO public.market_data_watch_universe(symbol,asset_group,timeframe,is_enabled,reason,updated_at)
VALUES('VIU6@RTSX','VOLATILITY','M1',true,'RVI-9.26 regime feature; Shadow only',clock_timestamp())
ON CONFLICT(symbol) DO UPDATE SET asset_group=excluded.asset_group,timeframe=excluded.timeframe,
 is_enabled=true,reason=excluded.reason,updated_at=clock_timestamp();

INSERT INTO public.futures_contract_universe(
 root_symbol,contract_symbol,asset_class,expiration_date,is_active,roll_priority,status,updated_at)
VALUES('VI','VIU6@RTSX','futures','2026-09-17',true,10,'RESEARCH',clock_timestamp())
ON CONFLICT DO NOTHING;

INSERT INTO marketcore.instrument_reference_v1(
 symbol,display_name,short_name,asset_class,exchange,board,currency,lot_size,
 min_price_step,price_scale,contract_size,expiration_date,is_active,is_tradable,
 first_seen,last_seen,updated_at,source,source_version,build_id)
VALUES('VIU6@RTSX','RVI, сентябрь 2026','RVI-9.26','FUTURE','MOEX','FUT','USD',1,
 0.05,2,1,'2026-09-17',true,false,clock_timestamp(),clock_timestamp(),clock_timestamp(),
 'MOEX_RVI_SPEC','RVI_SHADOW_FEATURE_ONBOARDING_V1',gen_random_uuid())
ON CONFLICT(symbol) DO UPDATE SET display_name=excluded.display_name,short_name=excluded.short_name,
 min_price_step=excluded.min_price_step,expiration_date=excluded.expiration_date,is_active=true,
 is_tradable=false,last_seen=clock_timestamp(),updated_at=clock_timestamp(),
 source=excluded.source,source_version=excluded.source_version,build_id=excluded.build_id;

INSERT INTO marketcore_ui.symbol_display_name_v1(symbol,display_name,asset_hint,source_version)
VALUES('VIU6@RTSX','Индекс волатильности RVI, сентябрь 2026','Индикатор','RVI_SHADOW_FEATURE_ONBOARDING_V1')
ON CONFLICT(symbol) DO UPDATE SET display_name=excluded.display_name,asset_hint=excluded.asset_hint,
 source_version=excluded.source_version,refreshed_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.rvi_regime_state_v1(
 id bigserial PRIMARY KEY,symbol text NOT NULL,bar_ts timestamptz NOT NULL,
 rvi_value numeric NOT NULL,rolling_percentile numeric NOT NULL CHECK(rolling_percentile BETWEEN 0 AND 1),
 regime_code text NOT NULL CHECK(regime_code IN('LOW_VOL','NORMAL_VOL','HIGH_VOL')),
 trading_allowed boolean NOT NULL DEFAULT false,paper_allowed boolean NOT NULL DEFAULT false,
 live_allowed boolean NOT NULL DEFAULT false,source_version text NOT NULL,
 calculated_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(symbol,bar_ts));

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES('RVI_REGIME_FEATURE','RVI_REGIME_FEATURE_V1',true,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,
 time '00:00',time '23:59',5,60,66,'RVI_SHADOW_FEATURE_ONBOARDING_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT ON analytics.rvi_regime_state_v1 TO alex,finam;
GRANT INSERT,UPDATE ON analytics.rvi_regime_state_v1 TO alex,finam;
GRANT USAGE,SELECT ON SEQUENCE analytics.rvi_regime_state_v1_id_seq TO alex,finam;

COMMIT;
