#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research_pipeline_orchestrator.py

grep -q "build_intermarket_regime_snapshot.py" src/scripts/research_pipeline_orchestrator.py
grep -q "sync_runtime_strategy_scores_from_selection.py" src/scripts/research_pipeline_orchestrator.py
grep -q "apply_intermarket_selection_modifier.py" src/scripts/research_pipeline_orchestrator.py
grep -q "apply_active_contract_lifecycle_filter.py" src/scripts/research_pipeline_orchestrator.py
grep -q 'symbol="GLOBAL"' src/scripts/research_pipeline_orchestrator.py

echo "RESEARCH_PIPELINE_INTERMARKET_RUNTIME_WIRING_OK"
