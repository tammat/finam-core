#!/usr/bin/env bash
set -euo pipefail

python -m py_compile src/scripts/research_pipeline_orchestrator.py

grep -q "build_trade_context_envelopes.py" src/scripts/research_pipeline_orchestrator.py
grep -q "analytics/build_trade_context_envelopes.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_edge_validation_table.py" src/scripts/research_pipeline_orchestrator.py

echo "RESEARCH_PIPELINE_TRADE_CONTEXT_ENVELOPE_WIRING_TEST_OK"
