INSERT INTO analytics.edge_configuration_v1
(edge_name, enabled, config_json, source_version, build_id)
VALUES
(
  'EDGE_DISCOVERY_LOOP',
  true,
  jsonb_build_object(
    'profile', 'QUALIFIED',
    'discovery_enabled', true,
    'interval_minutes', 60,
    'max_parallel_research_jobs', 8,
    'max_new_parameter_searches_per_day', 100,
    'max_active_sprints', 1,
    'min_candidate_score', 0.60,
    'min_expectancy', 0.0,
    'min_profit_factor', 1.20,
    'max_drawdown_pct', 15.0,
    'paper_candidates_limit', 20,
    'auto_recommendation', true,
    'auto_queue', true,
    'auto_paper', false,
    'market_data_max_age_sec', 900
  ),
  'EDGE_DISCOVERY_LOOP_CONFIG_V1',
  'manual'
)
ON CONFLICT(edge_name) DO UPDATE SET
  enabled=EXCLUDED.enabled,
  config_json=analytics.edge_configuration_v1.config_json || EXCLUDED.config_json,
  source_version='EDGE_DISCOVERY_LOOP_CONFIG_V1',
  updated_at=now();

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_configuration_v1 TO alex;

GRANT USAGE ON SCHEMA analytics TO alex;

GRANT USAGE ON SCHEMA analytics TO alex;
