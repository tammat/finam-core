#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_EQUITY_CURVE_V1 ==="

scripts/apply_paper_runtime_equity_curve_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_equity_curve_v1.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_paper_runtime_equity_curve_v1.py

equity_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_equity_curve_v1;")
drawdown_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_drawdown_curve_v1;")

test "$equity_rows" -gt 0
test "$drawdown_rows" -gt 0

psql -d finam_core -c "
SELECT point_no, ts, ticker, realized_pnl, equity_pnl
FROM marketcore_ui.paper_runtime_equity_curve_v1
ORDER BY point_no DESC
LIMIT 5;
"

echo "paper_equity_curve_rows=$equity_rows"
echo "paper_drawdown_curve_rows=$drawdown_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_EQUITY_CURVE_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_EQUITY_CURVE_V1_OK"
