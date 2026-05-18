#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/parameter_sweep_summary.py
python src/scripts/parameter_sweep_summary.py --help >/dev/null

echo "OK: parameter_sweep_summary compile"
