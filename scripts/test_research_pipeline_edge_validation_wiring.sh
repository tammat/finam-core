#!/usr/bin/env bash
set -euo pipefail

python -m py_compile src/scripts/research_pipeline_orchestrator.py

grep -q "build_intraday_pnl.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_edge_validation_table.py" src/scripts/research_pipeline_orchestrator.py
grep -q "ZoneInfo(\"Europe/Moscow\")" src/scripts/research_pipeline_orchestrator.py
grep -q "analytics/build_intraday_pnl.py" src/scripts/research_pipeline_orchestrator.py
grep -q "analytics/build_edge_validation_table.py" src/scripts/research_pipeline_orchestrator.py

echo "RESEARCH_PIPELINE_EDGE_VALIDATION_WIRING_TEST_OK"
