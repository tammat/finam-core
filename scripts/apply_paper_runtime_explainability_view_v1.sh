#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
    -v ON_ERROR_STOP=1 \
    -d finam_core \
    -f sql/marketcore_ui/010_paper_runtime_explainability_view_v1.sql

echo "PAPER_RUNTIME_EXPLAINABILITY_VIEW_V1_READY"
