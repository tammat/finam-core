#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

grep -q "UI v2" src/ui/templates/readonly_runtime_dashboard_v1.html
grep -q "Runtime Governance" src/ui/templates/readonly_runtime_dashboard_v1.html
grep -q "GOLD: накопление статистики" src/ui/templates/readonly_runtime_dashboard_v1.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true

grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

curl -s http://127.0.0.1:8088 | grep -q "Панель управления Finam_Core"

echo TEST_UI_RUNTIME_DASHBOARD_LAYOUT_V2_OK
