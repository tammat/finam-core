#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/build_directional_edge_guard.py

grep -q "CREATE VIEW directional_edge_guard_v1" sql/create_directional_edge_guard_v1.sql
grep -q "analytics_only" sql/create_directional_edge_guard_v1.sql
grep -q "insufficient_data" sql/create_directional_edge_guard_v1.sql
grep -q "favorable" sql/create_directional_edge_guard_v1.sql
grep -q "unfavorable" sql/create_directional_edge_guard_v1.sql

python src/scripts/build_directional_edge_guard.py --help | grep -q -- "--continuous-symbol"

echo "DIRECTIONAL_EDGE_GUARD_V1_COMPILE_OK"
