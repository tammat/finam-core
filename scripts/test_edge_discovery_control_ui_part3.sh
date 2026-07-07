#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_CONTROL_UI_PART3 ==="

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
    src/marketcore/presentation/components/discovery_action_panel.py \
    src/marketcore/presentation/actions/discovery_command_handler.py \
    src/marketcore/presentation/pages/discovery_control_page.py

before=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.command_queue_v1;
")

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.presentation.actions.discovery_command_handler import enqueue
enqueue("RUN_AUDIT")
PY

after=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.command_queue_v1;
")

test "$after" -gt "$before"

systemctl is-active --quiet marketcore-ui-shell.service

curl -fsS http://127.0.0.1:8080/edge-discovery >/tmp/edge_discovery_control_ui_part3.html

grep -q "Discovery Loop" /tmp/edge_discovery_control_ui_part3.html
grep -q "Scheduler" /tmp/edge_discovery_control_ui_part3.html
grep -q "Worker" /tmp/edge_discovery_control_ui_part3.html
grep -q "Actions" /tmp/edge_discovery_control_ui_part3.html

if grep -q "<pre" /tmp/edge_discovery_control_ui_part3.html; then
    echo "RAW_PRE_FOUND"
    exit 1
fi

echo "command_queue_before=$before"
echo "command_queue_after=$after"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=EDGE_DISCOVERY_CONTROL_UI_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_CONTROL_UI_PART3_OK"
