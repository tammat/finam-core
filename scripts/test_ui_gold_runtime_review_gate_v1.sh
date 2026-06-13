#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_gold_runtime_review_gate_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q '"/gold-runtime-review-gate"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "Gate GOLD" src/ui/templates/base.html
grep -q "GOLD: runtime review gate" src/ui/templates/gold_runtime_review_gate.html
grep -q "READY_FOR_RUNTIME_REVIEW" src/ui/templates/gold_runtime_review_gate.html || true

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/gold-runtime-review-gate | grep -q "GOLD: runtime review gate"
curl -s http://127.0.0.1:8088/gold-runtime-review-gate | grep -q "READY_FOR_RUNTIME_REVIEW"
curl -s http://127.0.0.1:8088/gold-runtime-review-gate | grep -q "up_impulse_sell_block"

echo TEST_UI_GOLD_RUNTIME_REVIEW_GATE_V1_OK
