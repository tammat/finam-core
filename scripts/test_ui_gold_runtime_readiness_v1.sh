#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_gold_runtime_readiness_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q '"/gold-readiness"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "Готовность GOLD" src/ui/templates/base.html
grep -q "Readiness Score" src/ui/templates/gold_readiness.html
grep -q "Готов к runtime-наблюдению" src/ui/templates/gold_readiness.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/gold-readiness | grep -q "GOLD: готовность к runtime-наблюдению"
curl -s http://127.0.0.1:8088/gold-readiness | grep -q "Readiness Score"
curl -s http://127.0.0.1:8088/gold-readiness | grep -q "Готов к runtime-наблюдению"

echo TEST_UI_GOLD_RUNTIME_READINESS_V1_OK
