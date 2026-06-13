#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "READY_FOR_RUNTIME_REVIEW" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Готов к ручному runtime-review" src/ui/readonly_runtime_dashboard_v1.py

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/runtime-candidates | grep -q "READY_FOR_RUNTIME_REVIEW"
curl -s http://127.0.0.1:8088/runtime-candidates | grep -q "Готов к ручному runtime-review"

echo TEST_UI_RUNTIME_CANDIDATES_REGISTRY_SYNC_V1_OK
