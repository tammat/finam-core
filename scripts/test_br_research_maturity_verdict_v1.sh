#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research/build_br_research_maturity_verdict_v1.py

grep -q "RESEARCH_WATCH_CONTAMINATED" src/scripts/research/build_br_research_maturity_verdict_v1.py
grep -q "runtime_enabled=False" src/scripts/research/build_br_research_maturity_verdict_v1.py
grep -q "repeatability_high_day_concentration" src/scripts/research/build_br_research_maturity_verdict_v1.py
grep -q "BR_RESEARCH_MATURITY_VERDICT_V1_OK" src/scripts/research/build_br_research_maturity_verdict_v1.py

echo "BR_RESEARCH_MATURITY_VERDICT_V1_TEST_OK"
