#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

test -f src/ui/templates/instruments.html

grep -q '@app.get("/instruments"' src/ui/readonly_runtime_dashboard_v1.py
grep -q 'href="/instruments"' src/ui/templates/base.html
grep -q "Статистика инструментов" src/ui/templates/instruments.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true

grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

curl -s http://127.0.0.1:8088/instruments | grep -q "Статистика инструментов"

echo TEST_UI_INSTRUMENT_STATISTICS_V1_OK
