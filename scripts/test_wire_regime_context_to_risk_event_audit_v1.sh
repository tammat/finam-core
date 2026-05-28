#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_WIRE_REGIME_CONTEXT_TO_RISK_EVENT_AUDIT_V1_START"

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/notifications/risk_notification_bridge_v1.py \
  src/finam_core/notifications/risk_event_audit_storage_v1.py

grep -q "wire_runtime_risk_events_to_audit_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q '"regime":' src/finam_core/pipelines/paper_pipeline.py
grep -q '"trend":' src/finam_core/pipelines/paper_pipeline.py
grep -q '"volatility":' src/finam_core/pipelines/paper_pipeline.py
grep -q '"atr":' src/finam_core/pipelines/paper_pipeline.py
grep -q '"atr_pct":' src/finam_core/pipelines/paper_pipeline.py
grep -q '"price":' src/finam_core/pipelines/paper_pipeline.py
grep -q '"tradable":' src/finam_core/pipelines/paper_pipeline.py
grep -q "state=st" src/finam_core/pipelines/paper_pipeline.py
grep -q "regime=regime" src/finam_core/pipelines/paper_pipeline.py
grep -q "price=price" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_WIRE_REGIME_CONTEXT_TO_RISK_EVENT_AUDIT_V1_OK"
