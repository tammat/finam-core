BEGIN;
UPDATE analytics.edge_search_scenario_v1 SET
 schedule_policy=schedule_policy || '{
   "max_parallel_cycles":1,
   "cpu_nice":15,
   "io_class":"best_effort",
   "io_priority":7,
   "estimated_cpu_cores":1,
   "protect_interactive_ui":true
 }'::jsonb,
 config_version='V2_RESOURCE_GOVERNED',updated_at=clock_timestamp()
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH';

UPDATE analytics.edge_search_scenario_step_v1 SET timeout_seconds=2400
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='DISCOVER_REGIME';
UPDATE analytics.edge_search_scenario_step_v1 SET timeout_seconds=3600
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='WALKFORWARD';
COMMIT;
