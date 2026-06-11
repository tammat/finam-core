#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true

grep -RniE \
"INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" \
src/ui && exit 1 || true

curl -s http://127.0.0.1:8088 | grep -q "Панель управления Finam_Core"

echo UI_READONLY_OK
echo TEST_UI_READONLY_RUNTIME_DASHBOARD_SMOKE_V1_OK
