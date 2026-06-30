#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OUT_OF_SAMPLE_VALIDATION_SCHEMA_AUDIT_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'existing_oos_tables=' || count(*)
FROM information_schema.tables
WHERE table_schema IN ('research','public')
  AND (
      lower(table_name) LIKE '%out_of_sample%'
   OR lower(table_name) LIKE '%oos%'
   OR lower(table_name) LIKE '%walkforward%'
   OR lower(table_name) LIKE '%validation%'
  );

SELECT 'existing_oos_table=' || table_schema || '.' || table_name
FROM information_schema.tables
WHERE table_schema IN ('research','public')
  AND (
      lower(table_name) LIKE '%out_of_sample%'
   OR lower(table_name) LIKE '%oos%'
   OR lower(table_name) LIKE '%walkforward%'
   OR lower(table_name) LIKE '%validation%'
  )
ORDER BY table_schema, table_name;

SELECT 'research_candidates_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='research'
  AND table_name='research_candidates_v1';

SELECT 'scorecard_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='research'
  AND table_name='analytics_global_edge_scorecard_v1';

SELECT 'forensic_report_table_exists=' || count(*)
FROM information_schema.tables
WHERE table_schema='research'
  AND table_name='global_edge_forensic_reports_v1';

SELECT 'forensic_report_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='research'
  AND table_name='global_edge_forensic_reports_v1';

SELECT 'candidate_oos_ready=' || count(*)
FROM research.global_edge_forensic_reports_v1
WHERE recommendation='PROMOTE_TO_OOS_VALIDATION'
  AND replay_status='PASS'
  AND robustness_status='PASS'
  AND micro_live_allowed=false
  AND runtime_changed=false;

SELECT 'oos_ready_candidate=' ||
       candidate_id || '|' ||
       symbol || '|' ||
       strategy || '|' ||
       timeframe || '|' ||
       recommendation
FROM research.global_edge_forensic_reports_v1
WHERE recommendation='PROMOTE_TO_OOS_VALIDATION'
  AND replay_status='PASS'
  AND robustness_status='PASS'
  AND micro_live_allowed=false
  AND runtime_changed=false
ORDER BY created_at DESC
LIMIT 10;

SELECT 'required_table=research.oos_validation_campaigns_v1';
SELECT 'required_table=research.oos_validation_results_v1';
SELECT 'required_table=research.oos_validation_decisions_v1';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=OUT_OF_SAMPLE_VALIDATION_SCHEMA_AUDIT_V1_READY';
SQL

echo "TEST_OUT_OF_SAMPLE_VALIDATION_SCHEMA_AUDIT_V1_OK"
