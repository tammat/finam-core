#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/edge_validation_engine.py \
  src/scripts/analytics/build_edge_validation_table.py

grep -q "analytics_edge_validation_v1" src/scripts/analytics/build_edge_validation_table.py
grep -q "v_edge_validation_ru" src/scripts/analytics/build_edge_validation_table.py
grep -q "v_edge_validation_summary_ru" src/scripts/analytics/build_edge_validation_table.py
grep -q "EdgeValidationEngine" src/scripts/analytics/build_edge_validation_table.py

echo "EDGE_VALIDATION_TABLE_V1_TEST_OK"
