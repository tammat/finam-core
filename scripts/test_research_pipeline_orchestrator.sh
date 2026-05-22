#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/research_pipeline_orchestrator.py

grep -q "build_trade_fill_quality_audit.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_closed_trade_reconstruction_v2.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_strategy_promotion_engine_v1.py" src/scripts/research_pipeline_orchestrator.py
grep -q "sync_runtime_active_universe_from_strategy_selection.py" src/scripts/research_pipeline_orchestrator.py

echo "TEST_RESEARCH_PIPELINE_ORCHESTRATOR_OK"
