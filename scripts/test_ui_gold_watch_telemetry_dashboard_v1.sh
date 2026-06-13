#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_gold_watch_telemetry_dashboard_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q '"/gold-watch-telemetry"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "Телеметрия GOLD" src/ui/templates/base.html
grep -q "GOLD: telemetry runtime-наблюдения" src/ui/templates/gold_watch_telemetry.html
grep -q "История telemetry" src/ui/templates/gold_watch_telemetry.html
grep -q "Shadow Profit Factor" src/ui/templates/gold_watch_telemetry.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/gold-watch-telemetry | grep -q "GOLD: telemetry runtime-наблюдения"
curl -s http://127.0.0.1:8088/gold-watch-telemetry | grep -q "WATCH_RUNTIME_ACTIVE"
curl -s http://127.0.0.1:8088/gold-watch-telemetry | grep -q "Shadow Profit Factor"

echo TEST_UI_GOLD_WATCH_TELEMETRY_DASHBOARD_V1_OK
