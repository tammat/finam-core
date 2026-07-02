#!/usr/bin/env bash
set -euo pipefail
sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/008_paper_runtime_summary_v1.sql
echo "PAPER_RUNTIME_REAL_DATA_SCHEMA_V1_READY"
