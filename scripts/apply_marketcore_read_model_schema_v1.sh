#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/001_marketcore_ui_schema.sql

echo "MARKETCORE_READ_MODEL_SCHEMA_V1_READY"
