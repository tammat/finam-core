#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/analyze_regime_performance.py

python src/scripts/analyze_regime_performance.py --help >/dev/null

echo "OK: analyze_regime_performance compile"
