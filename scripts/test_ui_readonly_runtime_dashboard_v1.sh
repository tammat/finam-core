#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/ui/readonly_runtime_dashboard_v1.py

grep -q "SELECT" src/ui/readonly_runtime_dashboard_v1.py

if grep -Eiq "INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE TABLE" \
  src/ui/readonly_runtime_dashboard_v1.py
then
  echo "UI_READONLY_AUDIT_FAIL_WRITE_SQL_FOUND"
  exit 1
fi

grep -q "Панель управления Finam_Core" \
  src/ui/templates/readonly_runtime_dashboard_v1.html

echo TEST_UI_READONLY_RUNTIME_DASHBOARD_V1_OK
