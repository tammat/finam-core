#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "def fetch_v3_dashboard_data" src/ui/readonly_runtime_dashboard_v1.py
grep -q "v3_dashboard.html" src/ui/readonly_runtime_dashboard_v1.py
grep -q "@app.get(\"/v3\"" src/ui/readonly_runtime_dashboard_v1.py

test -f src/ui/templates/v3_dashboard.html
grep -q "FINAM_CORE V3" src/ui/templates/v3_dashboard.html
grep -q "Текущий clean V3 контур" src/ui/templates/v3_dashboard.html
grep -q "Strategy statistics V3" src/ui/templates/v3_dashboard.html

echo TEST_UI_V3_DASHBOARD_SIMPLIFICATION_V1_OK
