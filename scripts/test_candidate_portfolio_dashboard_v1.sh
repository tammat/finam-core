#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_candidate_portfolio_dashboard_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q '"/candidate-portfolio"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "Портфель кандидатов" src/ui/templates/base.html
grep -q "Candidate Portfolio Dashboard" src/ui/templates/candidate_portfolio_dashboard.html
grep -q "Top Candidate" src/ui/templates/candidate_portfolio_dashboard.html

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/candidate-portfolio | grep -q "Candidate Portfolio Dashboard"
curl -s http://127.0.0.1:8088/candidate-portfolio | grep -q "GDU6@RTSX"
curl -s http://127.0.0.1:8088/candidate-portfolio | grep -q "Вынести на runtime-review"
curl -s http://127.0.0.1:8088/candidate-portfolio | grep -q "LKOH@MISX"
curl -s http://127.0.0.1:8088/candidate-portfolio | grep -q "USDRUBF@RTSX"
curl -s http://127.0.0.1:8088/candidate-portfolio | grep -q "BRN6@RTSX"
curl -s http://127.0.0.1:8088/candidate-portfolio | grep -q "NGN6@RTSX"
curl -s http://127.0.0.1:8088/candidate-portfolio | grep -q "Отключён"
curl -s http://127.0.0.1:8088/candidate-portfolio | grep -q "Отключено"

echo TEST_CANDIDATE_PORTFOLIO_DASHBOARD_V1_OK
