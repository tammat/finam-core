#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "ru_accumulation_status" src/ui/readonly_runtime_dashboard_v1.py
grep -q "ru_statistics_status" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Раннее накопление" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Идёт накопление" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Нет V3-цепочек" src/ui/readonly_runtime_dashboard_v1.py

grep -q "accumulation_status_ru" src/ui/templates/v3_dashboard.html
grep -q "statistics_status_ru" src/ui/templates/v3_dashboard.html

echo TEST_UI_V3_STATUS_TRANSLATION_V1_OK
