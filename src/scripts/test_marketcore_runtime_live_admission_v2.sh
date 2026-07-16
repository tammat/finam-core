#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/059_profit_funnel_runtime_live_admission_v2.sql >/dev/null
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_runtime_live_admission_v2.py
before="$(psql -d finam_core -Atqc "SELECT count(*) FROM public.orders")"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_profit_funnel_runtime_live_admission_v2.py
after="$(psql -d finam_core -Atqc "SELECT count(*) FROM public.orders")"
test "$before" = "$after"
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_runtime_live_admission_v2 WHERE broker_order_allowed OR execution_enabled OR live_allowed")" -eq 0
echo "real_orders_before=$before"
echo "real_orders_after=$after"
echo "execution_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_RUNTIME_LIVE_ADMISSION_V2_READY"
