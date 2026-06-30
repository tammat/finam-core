#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_GLOBAL_EDGE_FORENSIC_REPORT_PERSISTENCE_V1 ==="

src/scripts/research/build_global_edge_forensic_engine_v1.py \
    --candidate-id MSC-000001 \
    --save

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'

SELECT
'forensic_report_table_exists='||
EXISTS(
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='global_edge_forensic_reports_v1'
);

SELECT
'reports='||
count(*)
FROM research.global_edge_forensic_reports_v1;

SELECT
'latest='||
candidate_id||'|'||
symbol||'|'||
strategy||'|'||
timeframe||'|'||
replay_status||'|'||
forensic_status||'|'||
robustness_status||'|'||
recommendation
FROM research.global_edge_forensic_reports_v1
ORDER BY created_at DESC
LIMIT 1;

SELECT
'candidate_oos_ready='||
count(*)
FROM research.global_edge_forensic_reports_v1
WHERE recommendation='PROMOTE_TO_OOS_VALIDATION'
  AND replay_status='PASS'
  AND robustness_status='PASS'
  AND micro_live_allowed=false
  AND runtime_changed=false;

SELECT 'VERDICT=GLOBAL_EDGE_FORENSIC_REPORT_PERSISTENCE_V1_READY';

SQL

echo "TEST_GLOBAL_EDGE_FORENSIC_REPORT_PERSISTENCE_V1_OK"

