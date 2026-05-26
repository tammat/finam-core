#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/build_session_scorecard.py

grep -q "CREATE VIEW session_scorecard_v1" sql/create_session_scorecard_v1.sql
grep -q "session_bucket" sql/create_session_scorecard_v1.sql
grep -q "europe_open" sql/create_session_scorecard_v1.sql
grep -q "session_edge_status" sql/create_session_scorecard_v1.sql

python src/scripts/build_session_scorecard.py --help | grep -q -- "--continuous-symbol"

echo "SESSION_SCORECARD_V1_COMPILE_OK"
