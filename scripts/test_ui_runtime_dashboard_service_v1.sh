#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SERVICE_FILE="infra/finam-core-ui-readonly.service"

test -f "$SERVICE_FILE"

grep -q "ExecStart=/opt/finam-core/venv/bin/uvicorn ui.readonly_runtime_dashboard_v1:app" "$SERVICE_FILE"
grep -q "Environment=PYTHONPATH=src" "$SERVICE_FILE"
grep -q "WorkingDirectory=/opt/finam-core" "$SERVICE_FILE"
grep -q "Restart=always" "$SERVICE_FILE"
grep -q "NoNewPrivileges=true" "$SERVICE_FILE"

if grep -Eiq "INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP" "$SERVICE_FILE"
then
  echo "UI_SERVICE_AUDIT_FAIL_WRITE_TOKEN"
  exit 1
fi

echo TEST_UI_RUNTIME_DASHBOARD_SERVICE_V1_OK
