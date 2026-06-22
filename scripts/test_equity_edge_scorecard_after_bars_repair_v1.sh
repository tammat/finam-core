#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_EDGE_SCORECARD_AFTER_BARS_REPAIR_V1 ==="

curl -fsS http://127.0.0.1:8088/edge | tee /tmp/equity_edge_after_bars_repair_v1.html >/dev/null

grep -q "SBERP@MISX\|SFIN@MISX\|VTBR@MISX" /tmp/equity_edge_after_bars_repair_v1.html || true
grep -q "Технический рейтинг готовности\|Рейтинг Edge" /tmp/equity_edge_after_bars_repair_v1.html

echo "EDGE_PAGE_OK=1"

bash scripts/test_equity_no_bars_diagnostic_v2.sh
bash scripts/test_equity_bars_coverage_repair_plan_v1.sh

echo "VERDICT=EQUITY_EDGE_SCORECARD_AFTER_BARS_REPAIR_OK"
echo "TEST_EQUITY_EDGE_SCORECARD_AFTER_BARS_REPAIR_V1_OK"
