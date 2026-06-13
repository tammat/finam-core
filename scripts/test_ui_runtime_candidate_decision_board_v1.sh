#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_runtime_candidate_decision_board_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q '"/runtime-candidate-decision-board"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "Decision Board" src/ui/templates/base.html
grep -q "Runtime Candidate Decision Board" src/ui/templates/runtime_candidate_decision_board.html
grep -q "Вынести на runtime-review" src/ui/readonly_runtime_dashboard_v1.py

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/runtime-candidate-decision-board | grep -q "Runtime Candidate Decision Board"
curl -s http://127.0.0.1:8088/runtime-candidate-decision-board | grep -q "GDU6@RTSX"
curl -s http://127.0.0.1:8088/runtime-candidate-decision-board | grep -q "Вынести на runtime-review"
curl -s http://127.0.0.1:8088/runtime-candidate-decision-board | grep -q "PROMOTE_RUNTIME_REVIEW"

echo TEST_UI_RUNTIME_CANDIDATE_DECISION_BOARD_V1_OK
