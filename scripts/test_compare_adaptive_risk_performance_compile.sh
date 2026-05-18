#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/compare_adaptive_risk_performance.py
python src/scripts/compare_adaptive_risk_performance.py --help >/dev/null

echo "OK: compare adaptive risk performance compile"
