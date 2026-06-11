#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

if grep -q "source='closed_trade_engine_v1_1'" src/ui/readonly_runtime_dashboard_v1.py
then
  echo "UI_CLOSED_TRADES_SOURCE_FILTER_STILL_PRESENT"
  exit 1
fi

if grep -q "source IN ('closed_trade_engine_v1', 'closed_trade_engine_v1_1')" src/ui/readonly_runtime_dashboard_v1.py
then
  echo "UI_CLOSED_TRADES_SOURCE_IN_FILTER_STILL_PRESENT"
  exit 1
fi

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/instruments | grep -q "USDRUBF@RTSX"
curl -s http://127.0.0.1:8088/instruments | grep -q "LKOH@MISX"

echo TEST_UI_CLOSED_TRADES_UNIFIED_SOURCE_V1_OK
