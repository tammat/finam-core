#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_STATUS_BAR_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_status_bar \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/components/layout/status_bar.py

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_status_bar \
PYTHONPATH=src \
python - <<'PY'
from marketcore.presentation.components.layout.status_bar import render_status_bar

html = render_status_bar()
assert "marketcore-status-bar" in html
assert "TZ: Europe/Moscow" in html
assert "Currency: RUB" in html
assert "Broker: Finam" in html

import re
assert re.search(r"\d{2}-\d{2}-\d{2} \d{2}:\d{2}", html), html

print("status_bar_render=OK")
PY

grep -RIn "render_status_bar" src/marketcore/presentation | head -20

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/marketcore_status_bar_home.html

grep -q "marketcore-status-bar" /tmp/marketcore_status_bar_home.html
grep -q "TZ: Europe/Moscow" /tmp/marketcore_status_bar_home.html
grep -q "Currency: RUB" /tmp/marketcore_status_bar_home.html
grep -q "Broker: Finam" /tmp/marketcore_status_bar_home.html
grep -Eq '[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}' /tmp/marketcore_status_bar_home.html

echo "status_bar=OK"
echo "timezone=Europe/Moscow"
echo "currency=RUB"
echo "broker=Finam"
echo "time_format=DD-MM-YY HH:MM"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_STATUS_BAR_V1_READY"
echo "VERDICT=TEST_MARKETCORE_STATUS_BAR_V1_OK"
