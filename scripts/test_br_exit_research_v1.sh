#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_exit_research_v1.py

python3 src/scripts/analytics/build_br_exit_research_v1.py | \
  tee /tmp/br_exit_research_v1.log

grep -q "BR EXIT RESEARCH V1" /tmp/br_exit_research_v1.log
grep -q "BASELINE" /tmp/br_exit_research_v1.log
grep -q "CANDIDATE_EXITS" /tmp/br_exit_research_v1.log
grep -q "RANKING" /tmp/br_exit_research_v1.log
grep -q "WINNER_POLICY=" /tmp/br_exit_research_v1.log
grep -q "VERDICT=OK" /tmp/br_exit_research_v1.log

echo BR_EXIT_RESEARCH_V1_OK
