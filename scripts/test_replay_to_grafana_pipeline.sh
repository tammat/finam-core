#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

export PYTHONPATH=src
export REPLAY_DISABLE_BR_REGIME=1

BEFORE_COUNT=$(psql "$DATABASE_URL" -t -A -c "
SELECT COUNT(*)
FROM trades
WHERE trade_source='paper';
")

python -u src/scripts/replay_br_pipeline.py > /tmp/replay_test.log 2>&1

AFTER_COUNT=$(psql "$DATABASE_URL" -t -A -c "
SELECT COUNT(*)
FROM trades
WHERE trade_source='paper';
")

if [ "$AFTER_COUNT" -le "$BEFORE_COUNT" ]; then
    echo "ERROR: replay did not create new paper trades"
    exit 1
fi

VIEW_COUNT=$(psql "$DATABASE_URL" -t -A -c "
SELECT COUNT(*)
FROM v_trades_pnl_auto_ui
WHERE \"Источник\"='paper';
")

if [ "$VIEW_COUNT" -le 0 ]; then
    echo "ERROR: Grafana auto pnl view is empty"
    exit 1
fi

grep -q "STATUS=OK" /tmp/replay_test.log

echo "========================================="
echo "REPLAY_TO_GRAFANA_PIPELINE_TEST_OK"
echo "paper_trades_before=$BEFORE_COUNT"
echo "paper_trades_after=$AFTER_COUNT"
echo "grafana_rows=$VIEW_COUNT"
echo "========================================="
