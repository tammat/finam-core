#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/ui/build_runtime_candidates_dashboard_v1.py
python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

python3 src/scripts/ui/build_runtime_candidates_dashboard_v1.py \
  | tee /tmp/ui_runtime_candidates_dashboard_v1.log

grep -q "UI_RUNTIME_CANDIDATES_DASHBOARD_V1_OK" /tmp/ui_runtime_candidates_dashboard_v1.log
grep -q "symbol=GDU6@RTSX" /tmp/ui_runtime_candidates_dashboard_v1.log
grep -q "status=WATCH_RUNTIME_CANDIDATE" /tmp/ui_runtime_candidates_dashboard_v1.log

grep -q "table-wrap" src/ui/templates/base.html
grep -q "table class=\"wide\"" src/ui/templates/instruments.html
grep -q "status-cell" src/ui/templates/instruments.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/instruments | grep -q "GDU6@RTSX"

echo TEST_UI_RUNTIME_CANDIDATES_DASHBOARD_V1_OK
