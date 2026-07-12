#!/usr/bin/env bash
set -euo pipefail

PYTHONPYCACHEPREFIX=/tmp/edge_oos_control_center_pycache PYTHONPATH=src \
  .venv/bin/python -m py_compile \
  src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py \
  src/marketcore/presentation/router.py \
  src/marketcore/presentation/app.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
from marketcore.presentation.router import route, route_post

code, body = route('/workspace-v2/control-center/edge-oos')
assert code == 200
text = body.decode('utf-8')
for marker in (
    'OOS-проверка Momentum', 'Запустить OOS', 'OOS_FAIL',
    'Продвижение', 'LIVE: BLOCKED', 'edge-oos-control.js',
):
    assert marker in text, marker

code, body = route_post('/workspace-v2/control-center/edge-oos/run')
assert code == 200
assert 'Проверка завершена. Код: 0' in body.decode('utf-8')
print('render=ok')
print('run_action=ok')
PY

node --check src/marketcore/presentation/ui_runtime/assets/v1/edge_oos_control_v1.js
unsafe=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_candidate_v1 WHERE micro_live_allowed OR live_allowed;")
test "$unsafe" = "0"
echo "unsafe_live_rows=$unsafe"
echo "VERDICT=TEST_EDGE_OOS_CONTROL_CENTER_V1_OK"
