#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_instrument_statistics_v2" src/ui/readonly_runtime_dashboard_v1.py
grep -q "instrument_rows" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Статистика инструментов" src/ui/templates/instruments.html
grep -q "Последний бар" src/ui/templates/instruments.html
grep -q "Expectancy" src/ui/templates/instruments.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 1

curl -s http://127.0.0.1:8088/instruments | grep -q "Статистика инструментов"
curl -s http://127.0.0.1:8088/instruments | grep -q "GDU6@RTSX"
curl -s http://127.0.0.1:8088/instruments | grep -q "BRN6@RTSX"

echo TEST_UI_INSTRUMENT_STATISTICS_V2_OK
