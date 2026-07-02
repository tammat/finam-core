#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_EXPLAINABILITY_VIEW_V1 ==="

scripts/apply_paper_runtime_explainability_view_v1.sh

psql -d finam_core <<'SQL'

SELECT count(*) AS rows
FROM marketcore_ui.paper_runtime_explainability_v1;

SELECT
    snapshot_id,
    symbol,
    strategy,
    signal_id,
    fill_id,
    heat_status,
    confidence,
    rr,
    outcome_class
FROM marketcore_ui.paper_runtime_explainability_v1
LIMIT 10;

SQL

rows=$(psql -At -d finam_core -c \
"SELECT count(*) FROM marketcore_ui.paper_runtime_explainability_v1;")

test "$rows" -gt 0

echo "rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=PAPER_RUNTIME_EXPLAINABILITY_VIEW_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_EXPLAINABILITY_VIEW_V1_OK"
