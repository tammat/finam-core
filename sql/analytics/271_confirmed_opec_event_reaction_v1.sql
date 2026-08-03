BEGIN;

UPDATE analytics.market_event_risk_v1
SET event_code='OPEC_PLUS_2026_08_02_CONFIRMED',
    updated_at=clock_timestamp()
WHERE event_code='OPEC_PLUS_2026_08_02_AWAITING';

CREATE TABLE IF NOT EXISTS analytics.market_event_confirmation_v1(
 event_code text PRIMARY KEY,confirmation_status text NOT NULL,
 expected_adjustment_kbd numeric,actual_adjustment_kbd numeric,surprise_kbd numeric,
 application_month date,next_meeting_date date,directional_signal boolean NOT NULL DEFAULT false,
 source_url text NOT NULL,confirmed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_version text NOT NULL DEFAULT 'MARKET_EVENT_CONFIRMATION_V1'
);

INSERT INTO analytics.market_event_confirmation_v1(
 event_code,confirmation_status,expected_adjustment_kbd,actual_adjustment_kbd,
 surprise_kbd,application_month,next_meeting_date,directional_signal,source_url
) VALUES (
 'OPEC_PLUS_2026_08_02_CONFIRMED','CONFIRMED',188,188,0,
 date '2026-09-01',date '2026-09-06',false,
 'https://www.opec.org/pr-detail/611-2-august-2026.html'
) ON CONFLICT(event_code) DO UPDATE SET
 confirmation_status=excluded.confirmation_status,
 expected_adjustment_kbd=excluded.expected_adjustment_kbd,
 actual_adjustment_kbd=excluded.actual_adjustment_kbd,surprise_kbd=excluded.surprise_kbd,
 application_month=excluded.application_month,next_meeting_date=excluded.next_meeting_date,
 directional_signal=false,source_url=excluded.source_url,confirmed_at=clock_timestamp();

UPDATE public.market_event_calendar
SET raw_json=raw_json || '{"expected_adjustment_kbd":188,"actual_adjustment_kbd":188,"surprise_kbd":0,"directional_signal":false}'::jsonb,
    updated_at=clock_timestamp()
WHERE source='OPEC' AND event_type='OPEC_PLUS_DECISION'
  AND event_time=timestamptz '2026-08-03 00:40:00+03';

CREATE TABLE IF NOT EXISTS analytics.market_event_reaction_shadow_v1(
 id bigserial PRIMARY KEY,event_code text NOT NULL,symbol text NOT NULL,
 event_ts timestamptz NOT NULL,first_market_bar_ts timestamptz NOT NULL,
 horizon_minutes integer NOT NULL CHECK(horizon_minutes IN(15,30,60)),
 baseline_close numeric NOT NULL,horizon_close numeric NOT NULL,
 return_pct numeric NOT NULL,move_atr numeric,relative_volume numeric,
 direction_code text NOT NULL CHECK(direction_code IN('UP','DOWN','FLAT')),
 directional_signal boolean NOT NULL DEFAULT false,
 source_version text NOT NULL DEFAULT 'MARKET_EVENT_REACTION_SHADOW_V1',
 calculated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(event_code,symbol,horizon_minutes)
);

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version
) VALUES (
 'MARKET_EVENT_REACTION_SHADOW','MARKET_EVENT_REACTION_SHADOW_V1',true,
 'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',5,90,64,
 'MARKET_EVENT_REACTION_SHADOW_V1'
) ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,
 enabled=true,interval_minutes=excluded.interval_minutes,priority=excluded.priority,
 config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT ON analytics.market_event_reaction_shadow_v1 TO alex,finam;
GRANT INSERT,UPDATE ON analytics.market_event_reaction_shadow_v1 TO alex,finam;
GRANT USAGE,SELECT ON SEQUENCE analytics.market_event_reaction_shadow_v1_id_seq TO alex,finam;
GRANT SELECT ON analytics.market_event_confirmation_v1 TO alex,finam;

COMMIT;
