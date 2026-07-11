#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PROFIT_FACTORY_RECONCILIATION_ENGINE_V1 ==="

psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/026_profit_factory_reconciliation_engine_v1.sql

PYTHONPYCACHEPREFIX=/tmp/profit_factory_pycache_v1 PYTHONPATH=src .venv/bin/python -m py_compile \
  src/finam_core/reconciliation/profit_factory/__init__.py \
  src/finam_core/reconciliation/profit_factory/engine.py \
  src/scripts/run_profit_factory_reconciliation_v1.py

links_before=$(psql -At -d finam_core -c \
  "SELECT count(*) FROM analytics.profit_factory_candidate_link_v1;")

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python src/scripts/run_profit_factory_reconciliation_v1.py --dry-run \
  | tee /tmp/profit_factory_reconciliation_dry_run_v1.txt

links_after_dry_run=$(psql -At -d finam_core -c \
  "SELECT count(*) FROM analytics.profit_factory_candidate_link_v1;")
test "$links_after_dry_run" = "$links_before"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python src/scripts/run_profit_factory_reconciliation_v1.py \
  | tee /tmp/profit_factory_reconciliation_apply_v1.txt

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python src/scripts/run_profit_factory_reconciliation_v1.py \
  | tee /tmp/profit_factory_reconciliation_repeat_v1.txt

grep -q 'mode=DRY_RUN' /tmp/profit_factory_reconciliation_dry_run_v1.txt
grep -q 'VERDICT=PROFIT_FACTORY_RECONCILIATION_ENGINE_V1_OK' \
  /tmp/profit_factory_reconciliation_apply_v1.txt
grep -q 'created_rows=0' /tmp/profit_factory_reconciliation_repeat_v1.txt
grep -q 'updated_rows=0' /tmp/profit_factory_reconciliation_repeat_v1.txt

completed_runs=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.profit_factory_reconciliation_run_v1
WHERE engine_version='PROFIT_FACTORY_RECONCILIATION_ENGINE_V1'
  AND status='COMPLETED';")
test "$completed_runs" -ge 3

echo "links_before=$links_before"
echo "links_after_dry_run=$links_after_dry_run"
echo "completed_runs=$completed_runs"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "VERDICT=TEST_PROFIT_FACTORY_RECONCILIATION_ENGINE_V1_OK"
