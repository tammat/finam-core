#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/research_pipeline_run_log.py \
  src/scripts/research_pipeline_orchestrator.py

grep -q "research_pipeline_runs" src/finam_core/analytics/research_pipeline_run_log.py
grep -q "research_pipeline_step_events" src/finam_core/analytics/research_pipeline_run_log.py
grep -q "run_id=" src/scripts/research_pipeline_orchestrator.py

echo "TEST_RESEARCH_PIPELINE_RUN_LOG_OK"
