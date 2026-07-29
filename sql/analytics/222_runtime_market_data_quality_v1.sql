BEGIN;

CREATE OR REPLACE VIEW analytics.runtime_market_data_quality_v1 AS
WITH active AS (
    SELECT symbol, upper(coalesce(nullif(timeframe, ''), 'M5')) AS timeframe
    FROM runtime_active_universe
    WHERE is_enabled
), local_clock AS (
    SELECT clock_timestamp() AS now_utc,
           clock_timestamp() AT TIME ZONE 'Europe/Moscow' AS now_msk
), prepared AS (
    SELECT a.symbol,a.timeframe,c.now_utc,c.now_msk,
           CASE WHEN a.timeframe='M1' THEN 60 ELSE 300 END AS interval_seconds,
           CASE
             WHEN extract(isodow FROM c.now_msk) BETWEEN 1 AND 5 AND a.symbol LIKE '%@MISX'
               THEN c.now_msk::time >= time '06:50' AND c.now_msk::time < time '23:50'
             WHEN extract(isodow FROM c.now_msk) BETWEEN 1 AND 5 AND a.symbol LIKE '%@RTSX'
               THEN c.now_msk::time >= time '09:00' AND c.now_msk::time < time '23:50'
             WHEN extract(isodow FROM c.now_msk) IN (6,7)
               THEN c.now_msk::time >= time '10:00' AND c.now_msk::time < time '19:00'
             ELSE false
           END AS session_open
    FROM active a CROSS JOIN local_clock c
), quality AS (
    SELECT p.*,b.latest_bar,b.bar_count,b.maximum_gap_seconds,cost.verified_at
    FROM prepared p
    LEFT JOIN LATERAL (
      SELECT max(ts) AS latest_bar,count(*)::int AS bar_count,
             max(gap_seconds) AS maximum_gap_seconds
      FROM (
        SELECT ts,extract(epoch FROM(ts-lag(ts) OVER(ORDER BY ts))) AS gap_seconds
        FROM (
          SELECT ts FROM market_bars
          WHERE symbol=p.symbol AND timeframe=p.timeframe
            AND ts + p.interval_seconds*interval '1 second' <= p.now_utc
          ORDER BY ts DESC LIMIT 4
        ) recent ORDER BY ts
      ) sequenced
    ) b ON true
    LEFT JOIN analytics.market_contract_cost_spec_v1 cost ON cost.symbol=p.symbol
)
SELECT symbol,timeframe,session_open,latest_bar,
       extract(epoch FROM(now_utc-latest_bar))::int AS age_seconds,
       bar_count,maximum_gap_seconds,verified_at AS cost_verified_at,
       CASE
         WHEN NOT session_open THEN 'OUT_OF_SESSION'
         WHEN latest_bar IS NULL OR bar_count<3 THEN 'NO_COMPLETED_BARS'
         WHEN extract(epoch FROM(now_utc-latest_bar)) > CASE WHEN timeframe='M1' THEN 180 ELSE 420 END THEN 'STALE'
         WHEN maximum_gap_seconds > interval_seconds*1.5 THEN 'GAP'
         WHEN symbol LIKE '%@RTSX' AND (verified_at IS NULL OR verified_at < now_utc-interval '48 hours') THEN 'COST_SPEC_STALE'
         ELSE 'READY'
       END AS quality_code
FROM quality;

GRANT SELECT ON analytics.runtime_market_data_quality_v1 TO alex,finam;

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version
) VALUES(
 'CONTRACT_SPEC_SYNC_INTRADAY','CONTRACT_SPEC_SYNC_V1',true,'Europe/Moscow',
 '[0,1,2,3,4]'::jsonb,'06:30','23:30',60,900,18,'V5_DATA_QUALITY_V1'
) ON CONFLICT(job_code) DO UPDATE SET
 enabled=true,interval_minutes=60,window_start='06:30',window_end='23:30',
 priority=18,config_version='V5_DATA_QUALITY_V1',updated_at=clock_timestamp();

COMMIT;
