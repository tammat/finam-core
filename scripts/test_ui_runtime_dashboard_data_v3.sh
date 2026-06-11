#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "runtime_edge_validation_scorecard_v2" src/ui/readonly_runtime_dashboard_v1.py
grep -q "runtime_shadow_gold_signals" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Последние checkpoint" src/ui/templates/readonly_runtime_dashboard_v1.html
grep -q "UI v3" src/ui/templates/readonly_runtime_dashboard_v1.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true

grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

curl -s http://127.0.0.1:8088 | grep -q "Runtime Edge Scorecard v2"

echo TEST_UI_RUNTIME_DASHBOARD_DATA_V3_OK
