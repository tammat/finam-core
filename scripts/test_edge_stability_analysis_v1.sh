#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/build_edge_stability_analysis.py

grep -q "CREATE VIEW edge_stability_analysis_v1" sql/create_edge_stability_analysis_v1.sql
grep -q "ntile(4)" sql/create_edge_stability_analysis_v1.sql
grep -q "stability_status" sql/create_edge_stability_analysis_v1.sql
grep -q "unstable_sign_flip" sql/create_edge_stability_analysis_v1.sql

python src/scripts/build_edge_stability_analysis.py --help | grep -q -- "--continuous-symbol"

echo "EDGE_STABILITY_ANALYSIS_V1_COMPILE_OK"
