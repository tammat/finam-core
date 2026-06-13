#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_runtime_candidate_scorecard_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q '"/runtime-candidate-scorecard"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "Scorecard кандидатов" src/ui/templates/base.html
grep -q "Runtime Candidate Scorecard" src/ui/templates/runtime_candidate_scorecard.html
grep -q "READY_FOR_RUNTIME_REVIEW" src/ui/readonly_runtime_dashboard_v1.py

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/runtime-candidate-scorecard | grep -q "Runtime Candidate Scorecard"
curl -s http://127.0.0.1:8088/runtime-candidate-scorecard | grep -q "GDU6@RTSX"
curl -s http://127.0.0.1:8088/runtime-candidate-scorecard | grep -q "Готов к ручному runtime-review"
curl -s http://127.0.0.1:8088/runtime-candidate-scorecard | grep -q "GOLD_SHADOW_FILTERED"

echo TEST_UI_RUNTIME_CANDIDATE_SCORECARD_V1_OK
