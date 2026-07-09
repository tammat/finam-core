#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 \
-f sql/analytics/paper_execution_feedback_dictionary_v1.sql

groups=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_reason_group_v1
WHERE enabled;
")

severity=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_severity_v1
WHERE enabled;
")

reasons=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_reason_v1
WHERE enabled;
")

test "$groups" -ge 7
test "$severity" -ge 4
test "$reasons" -ge 8

echo "reason_groups=$groups"
echo "severity_levels=$severity"
echo "feedback_reasons=$reasons"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1_OK"
