#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_runtime_candidate_lifecycle_board_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q '"/runtime-candidate-lifecycle"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "Lifecycle кандидатов" src/ui/templates/base.html
grep -q "Runtime Candidate Lifecycle Board" src/ui/templates/runtime_candidate_lifecycle_board.html
grep -q "REGISTRY" src/ui/templates/runtime_candidate_lifecycle_board.html || true

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/runtime-candidate-lifecycle | grep -q "Runtime Candidate Lifecycle Board"
curl -s http://127.0.0.1:8088/runtime-candidate-lifecycle | grep -q "GDU6@RTSX"
curl -s http://127.0.0.1:8088/runtime-candidate-lifecycle | grep -q "Вынести на runtime-review"
curl -s http://127.0.0.1:8088/runtime-candidate-lifecycle | grep -q "LKOH@MISX"
curl -s http://127.0.0.1:8088/runtime-candidate-lifecycle | grep -q "USDRUBF@RTSX"
curl -s http://127.0.0.1:8088/runtime-candidate-lifecycle | grep -q "BRN6@RTSX"
curl -s http://127.0.0.1:8088/runtime-candidate-lifecycle | grep -q "NGN6@RTSX"

echo TEST_UI_RUNTIME_CANDIDATE_LIFECYCLE_BOARD_V1_OK
