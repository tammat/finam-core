#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "WATCH_RUNTIME_CANDIDATE" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Кандидат для runtime-наблюдения" src/ui/templates/instruments.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/instruments \
  | grep -q "Кандидат для runtime-наблюдения"

echo TEST_UI_GOLD_PROMOTION_STATUS_V1_OK
