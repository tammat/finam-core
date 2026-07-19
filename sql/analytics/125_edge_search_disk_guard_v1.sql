BEGIN;
UPDATE analytics.edge_search_scenario_v1 SET
 schedule_policy=schedule_policy || '{"min_disk_free_gb":20,"limits_source":"DATABASE","sequential_funnels":true,"ui_reads_aggregates_only":true}'::jsonb,
 config_version='V5_DB_RESOURCE_GUARDED',updated_at=clock_timestamp()
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH';
COMMIT;
