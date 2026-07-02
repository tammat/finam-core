#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/009_paper_runtime_equity_curve_v1.sql

echo "PAPER_RUNTIME_EQUITY_CURVE_SCHEMA_V1_READY"
