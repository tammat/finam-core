#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export PAGER=cat
export PSQL_PAGER=cat

python -m py_compile src/scripts/analytics_data_quality_report.py

python src/scripts/analytics_data_quality_report.py \
  --out /tmp/analytics_data_quality_report.tsv

grep -E \
  "SIGNALS_DATA_QUALITY|CLOSED_TRADES_DATA_QUALITY|TRADES_ORIGIN_BREAKDOWN|INVALID_TRADE_SOURCE_VALUES" \
  /tmp/analytics_data_quality_report.tsv >/dev/null

echo "OK: analytics data quality report"
