#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

for template in base.html dashboard.html governance.html gold.html signals.html checkpoints.html
do
  test -f "src/ui/templates/$template"
done

grep -q '@app.get("/governance"' src/ui/readonly_runtime_dashboard_v1.py
grep -q '@app.get("/gold"' src/ui/readonly_runtime_dashboard_v1.py
grep -q '@app.get("/signals"' src/ui/readonly_runtime_dashboard_v1.py
grep -q '@app.get("/checkpoints"' src/ui/readonly_runtime_dashboard_v1.py

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true

grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

curl -s http://127.0.0.1:8088/ | grep -q "Панель управления Finam_Core"
curl -s http://127.0.0.1:8088/governance | grep -q "Runtime Governance"
curl -s http://127.0.0.1:8088/gold | grep -q "GOLD: накопление статистики"
curl -s http://127.0.0.1:8088/signals | grep -q "Последние GOLD shadow-сигналы"
curl -s http://127.0.0.1:8088/checkpoints | grep -q "Последние checkpoint проекта"

echo TEST_UI_RUNTIME_DASHBOARD_NAVIGATION_V1_OK
