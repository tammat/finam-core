#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_WIRE_RUNTIME_RISK_EVENTS_TO_AUDIT_V1_START"

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/notifications/risk_notification_bridge_v1.py \
  src/finam_core/notifications/risk_event_audit_storage_v1.py

grep -q "_audit_runtime_risk_event_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_RUNTIME_RISK_EVENT_AUDIT_OK" src/finam_core/pipelines/paper_pipeline.py
grep -q "wire_runtime_risk_events_to_audit_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "RiskNotificationInputV1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_RISK_REJECT" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_WIRE_RUNTIME_RISK_EVENTS_TO_AUDIT_V1_OK"
