#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/002_marketcore_ui_grants.sql

echo "MARKETCORE_UI_GRANTS_V1_READY"
