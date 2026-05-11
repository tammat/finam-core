#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q 'def log_risk_event(self, symbol=None, event="risk_event", decision=None, payload=None)' src/finam_core/storage/postgres_logger.py

! grep -R "log_risk_event(.*event_type=" src/finam_core --exclude-dir="__pycache__"

grep -R "log_risk_event(" src/finam_core/pipelines src/finam_core/risk --exclude-dir="__pycache__" >/dev/null

python -m py_compile src/finam_core/pipelines/paper_pipeline.py
python -m py_compile src/finam_core/storage/postgres_logger.py
python -m py_compile src/finam_core/risk/unified_decision.py

echo "LOG_RISK_EVENT_SIGNATURE_TEST_OK"
