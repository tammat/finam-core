#!/usr/bin/env bash
set -euo pipefail

python -m py_compile src/scripts/research_pipeline_orchestrator.py

grep -q "build_regime_aware_edge_v1.py" \
    src/scripts/research_pipeline_orchestrator.py

grep -q "analytics/build_regime_aware_edge_v1.py" \
    src/scripts/research_pipeline_orchestrator.py

grep -q "build_trade_context_envelopes.py" \
    src/scripts/research_pipeline_orchestrator.py

grep -q "build_edge_validation_table.py" \
    src/scripts/research_pipeline_orchestrator.py

echo "RESEARCH_PIPELINE_REGIME_EDGE_WIRING_TEST_OK"
