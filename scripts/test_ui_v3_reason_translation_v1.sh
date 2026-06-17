#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "def ru_reason" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Недостаточно полных V3-цепочек" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Идёт накопление данных для анализа" src/ui/readonly_runtime_dashboard_v1.py
grep -q "Сделки есть, но V3-цепочки не сформированы" src/ui/readonly_runtime_dashboard_v1.py

grep -q "accumulation_reason_ru" src/ui/templates/v3_dashboard.html
grep -q "statistics_reason_ru" src/ui/templates/v3_dashboard.html

echo TEST_UI_V3_REASON_TRANSLATION_V1_OK
