#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q '"/gold-details"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "fetch_gold_research_details_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Исследование золота" src/ui/templates/base.html
grep -q "Метрики shadow-проверки" src/ui/templates/gold_details.html
grep -q "Проверки" src/ui/templates/gold_details.html
grep -q "Последние сигналы" src/ui/templates/gold_details.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/gold-details | grep -q "Исследование золота"
curl -s http://127.0.0.1:8088/gold-details | grep -q "Кандидат для runtime-наблюдения"
curl -s http://127.0.0.1:8088/gold-details | grep -q "WATCH_RUNTIME_CANDIDATE"

echo TEST_UI_GOLD_RESEARCH_DETAILS_V1_OK
