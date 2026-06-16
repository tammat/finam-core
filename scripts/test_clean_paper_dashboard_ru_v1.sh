#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/observability/build_clean_paper_dashboard_ru_v1.py \
  src/ui/readonly_runtime_dashboard_v1.py

python3 src/scripts/observability/build_clean_paper_dashboard_ru_v1.py \
  | tee /tmp/clean_paper_dashboard_ru_v1.log

grep -q "ЧИСТЫЙ PAPER-КОНТУР V3" /tmp/clean_paper_dashboard_ru_v1.log
grep -q "Подтверждённый edge: нет" /tmp/clean_paper_dashboard_ru_v1.log
grep -q "CLEAN_PAPER_DASHBOARD_RU_V1_OK" /tmp/clean_paper_dashboard_ru_v1.log

curl -s http://127.0.0.1:8088/clean-paper-v3 \
  | tee /tmp/clean_paper_v3_8088.html \
  | grep -q "Чистый paper-контур V3"

grep -q "Подтверждённый edge: нет" /tmp/clean_paper_v3_8088.html
grep -q "Legacy scorecard" /tmp/clean_paper_v3_8088.html

echo TEST_CLEAN_PAPER_DASHBOARD_RU_V1_OK
