BEGIN;
UPDATE analytics.edge_search_scenario_v1 SET
 schedule_policy=schedule_policy || '{
   "timezone":"Europe/Moscow",
   "weekday_low_load_window":"00:00-08:59",
   "weekend_low_load_window":"00:00-23:59",
   "cron_weekday":"30 00 * * 1-5",
   "cron_weekend":"30 04,10,16,22 * * 6,0",
   "max_load_1m":2.5,
   "min_memory_available_mb":3072,
   "paper_shadow_priority_during_market_hours":true,
   "resource_skip_is_audited":true
 }'::jsonb,
 config_version='V3_SESSION_AND_LOAD_GOVERNED',updated_at=clock_timestamp()
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH';
COMMIT;
