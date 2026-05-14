#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/profit_lock_event_repository.py \
  src/finam_core/pipelines/paper_pipeline.py

python -m json.tool ops/grafana/dashboards/finam-mobile.json >/dev/null

grep -q "Profit Lock Stop Movement" ops/grafana/dashboards/finam-mobile.json
grep -q "profit_lock_events" ops/grafana/dashboards/finam-mobile.json
grep -q "PROFIT_LOCK_EVENT_LOG_FAILED" src/finam_core/execution/profit_lock_event_repository.py

echo "OK: profit lock events and grafana configured"
