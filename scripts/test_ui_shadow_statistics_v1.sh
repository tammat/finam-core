#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "gold_shadow_raw" src/ui/readonly_runtime_dashboard_v1.py
grep -q "shadow_trades" src/ui/readonly_runtime_dashboard_v1.py
grep -q "shadow_profit_factor" src/ui/readonly_runtime_dashboard_v1.py

grep -q "Shadow Signals" src/ui/templates/instruments.html
grep -q "Shadow Trades" src/ui/templates/instruments.html
grep -q "Shadow Expectancy" src/ui/templates/instruments.html
grep -q "Shadow Profit Factor" src/ui/templates/instruments.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/instruments | grep -q "GDU6@RTSX"
curl -s http://127.0.0.1:8088/instruments | grep -q "Shadow Signals"
curl -s http://127.0.0.1:8088/instruments | grep -q "Кандидат для runtime-наблюдения"

echo TEST_UI_SHADOW_STATISTICS_V1_OK
