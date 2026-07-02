#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/005_capital_manager_summary_v1.sql

echo "MARKETCORE_CAPITAL_MANAGER_SCHEMA_V1_READY"
