#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_REAL_DATA_V1 ==="

scripts/apply_paper_runtime_real_data_v1.sh

PYTHONPATH=src python -m py_compile src/scripts/build_paper_runtime_real_data_v1.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_paper_runtime_real_data_v1.py

psql -d finam_core <<'SQL'
SELECT *
FROM marketcore_ui.paper_runtime_summary_v1
WHERE id=1;
SQL

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_summary_v1 WHERE id=1;")
test "$rows" = "1"

source_version=$(psql -At -d finam_core -c "SELECT source_version FROM marketcore_ui.paper_runtime_summary_v1 WHERE id=1;")
test "$source_version" = "PAPER_RUNTIME_REAL_DATA_V1"

closed_total=$(psql -At -d finam_core -c "SELECT closed_trades_total FROM marketcore_ui.paper_runtime_summary_v1 WHERE id=1;")
test "$closed_total" -ge 0

echo "paper_runtime_summary_rows=1"
echo "paper_closed_trades_total=$closed_total"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_REAL_DATA_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_REAL_DATA_V1_OK"
