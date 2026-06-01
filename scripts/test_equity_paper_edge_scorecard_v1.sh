#!/usr/bin/env bash
set -euo pipefail

echo "TEST_EQUITY_PAPER_EDGE_SCORECARD_V1_START"

python3 src/scripts/analytics/build_equity_paper_edge_scorecard_v1.py \
  --symbols PLZL@MISX,LKOH@MISX,SBER@MISX \
  | grep -E "EQUITY_PAPER_EDGE_SCORECARD_V1|EQUITY_EDGE_ROW|EQUITY_EDGE_SUMMARY|EQUITY_PAPER_EDGE_SCORECARD_V1_OK"

echo "TEST_EQUITY_PAPER_EDGE_SCORECARD_V1_OK"
