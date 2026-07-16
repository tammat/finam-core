#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/057_profit_funnel_shadow_paper_admission_v2.sql >/dev/null
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_shadow_paper_admission_v2.py
before="$(psql -d finam_core -Atqc "SELECT count(*) FROM public.closed_trades")"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/build_profit_funnel_shadow_paper_admission_v2.py
after="$(psql -d finam_core -Atqc "SELECT count(*) FROM public.closed_trades")"
test "$before" = "$after"
expected="$(psql -d finam_core -Atqc "SELECT count(*) FROM (SELECT DISTINCT cohort_id,incubator_candidate_id FROM analytics.forward_edge_shadow_trade_v1) q")"
assessed="$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_shadow_paper_admission_v2")"
test "$expected" = "$assessed"
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.profit_funnel_shadow_paper_admission_v2 WHERE paper_allowed OR runtime_allowed OR live_allowed")" -eq 0
echo "paper_closed_trades_before=$before"
echo "paper_closed_trades_after=$after"
echo "shadow_candidates_assessed=$assessed"
echo "execution_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_SHADOW_PAPER_ADMISSION_V2_READY"
