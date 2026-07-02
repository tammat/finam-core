#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/007_runtime_center_summary_v1.sql

echo "MARKETCORE_RUNTIME_CENTER_READ_MODEL_SCHEMA_V1_READY"
