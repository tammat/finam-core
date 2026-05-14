#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/take_profit_engine.py \
  src/finam_core/execution/take_profit_event_repository.py \
  src/finam_core/pipelines/paper_pipeline.py

python -m json.tool ops/grafana/dashboards/finam-mobile.json >/dev/null

grep -q "Take Profit Levels" ops/grafana/dashboards/finam-mobile.json
grep -q "take_profit_events" ops/grafana/dashboards/finam-mobile.json
grep -q "TAKE_PROFIT_EVENT_LOG_FAILED" src/finam_core/execution/take_profit_event_repository.py

echo "OK: take profit events and grafana configured"
