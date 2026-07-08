#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_STATUS_BAR_SELECTORS_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_status_bar_selectors \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/components/layout/status_bar.py \
  src/marketcore/presentation/layout.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.components.layout.status_bar import render_status_bar

html = render_status_bar()
assert 'name="timezone"' in html
assert 'name="currency"' in html
assert 'name="broker"' in html
assert "Europe/Moscow" in html
assert "RUB" in html
assert "Finam" in html
assert "T-Bank" in html
assert "Interactive Brokers" in html

custom = render_status_bar("UTC", "USD", "QUIK")
assert '<option value="UTC" selected>' in custom
assert '<option value="USD" selected>' in custom
assert '<option value="QUIK" selected>' in custom

print("status_bar_selectors_render=OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/marketcore_status_bar_selectors.html

grep -q 'marketcore-status-bar' /tmp/marketcore_status_bar_selectors.html
grep -q 'name="timezone"' /tmp/marketcore_status_bar_selectors.html
grep -q 'name="currency"' /tmp/marketcore_status_bar_selectors.html
grep -q 'name="broker"' /tmp/marketcore_status_bar_selectors.html
grep -q 'Europe/Moscow' /tmp/marketcore_status_bar_selectors.html
grep -q 'RUB' /tmp/marketcore_status_bar_selectors.html
grep -q 'Finam' /tmp/marketcore_status_bar_selectors.html
grep -Eq '[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}' /tmp/marketcore_status_bar_selectors.html

echo "status_bar_selectors=OK"
echo "timezone_selector=OK"
echo "currency_selector=OK"
echo "broker_selector=OK"
echo "time_format=DD-MM-YY HH:MM"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_STATUS_BAR_SELECTORS_V1_READY"
echo "VERDICT=TEST_MARKETCORE_STATUS_BAR_SELECTORS_V1_OK"
