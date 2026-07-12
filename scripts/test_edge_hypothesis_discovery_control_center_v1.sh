#!/usr/bin/env bash
set -euo pipefail

PYTHONPYCACHEPREFIX=/tmp/edge_hypothesis_control_pycache PYTHONPATH=src \
  .venv/bin/python -m py_compile \
  src/scripts/build_edge_hypothesis_discovery_v1.py \
  src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py
node --check src/marketcore/presentation/ui_runtime/assets/v1/edge_oos_control_v1.js

latest=$(psql -At -d finam_core -c "SELECT discovery_run_id FROM analytics.edge_hypothesis_result_v1 ORDER BY created_at DESC LIMIT 1;")
hypotheses=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_hypothesis_result_v1 WHERE discovery_run_id='$latest';")
markets=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM analytics.edge_hypothesis_result_v1 WHERE discovery_run_id='$latest';")
families=$(psql -At -d finam_core -c "SELECT count(DISTINCT strategy_family) FROM analytics.edge_hypothesis_result_v1 WHERE discovery_run_id='$latest';")
max_score=$(psql -At -d finam_core -c "SELECT max(hypothesis_score) FROM analytics.edge_hypothesis_result_v1 WHERE discovery_run_id='$latest';")
promoted=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_hypothesis_result_v1 WHERE discovery_run_id='$latest' AND promotion_allowed;")
unsafe=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_candidate_v1 WHERE micro_live_allowed OR live_allowed;")

test "$hypotheses" = "432"
test "$markets" = "12"
test "$families" = "3"
test "$(psql -At -d finam_core -c "SELECT ($max_score <= 100)::int;")" = "1"
test "$promoted" = "0"
test "$unsafe" = "0"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
from marketcore.presentation.router import route
code, body = route('/workspace-v2/control-center/edge-oos')
text = body.decode('utf-8')
assert code == 200
for marker in ('Поиск новых гипотез','432 комбинаций','12 рынков','3 семейства','Искать гипотезы','USDRUBF@RTSX'):
    assert marker in text, marker
print('control_center_render=ok')
PY

echo "hypotheses=$hypotheses"
echo "markets=$markets"
echo "families=$families"
echo "max_score=$max_score"
echo "promotion_allowed_rows=$promoted"
echo "unsafe_live_rows=$unsafe"
echo "VERDICT=TEST_EDGE_HYPOTHESIS_DISCOVERY_CONTROL_CENTER_V1_OK"
