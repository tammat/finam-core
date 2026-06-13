#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_gold_stability_monitor_dashboard_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q '"/gold-stability-monitor"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "Стабильность GOLD" src/ui/templates/base.html
grep -q "GOLD: монитор стабильности" src/ui/templates/gold_stability_monitor.html
grep -q "История расчётов" src/ui/templates/gold_stability_monitor.html
grep -q "Filtered PnL" src/ui/templates/gold_stability_monitor.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/gold-stability-monitor | grep -q "GOLD: монитор стабильности"
curl -s http://127.0.0.1:8088/gold-stability-monitor | grep -q "GOLD_STABILITY_MONITOR_READY_FOR_REVIEW"
curl -s http://127.0.0.1:8088/gold-stability-monitor | grep -q "Filtered PnL"

echo TEST_UI_GOLD_STABILITY_MONITOR_DASHBOARD_V1_OK
