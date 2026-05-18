#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/select_best_adaptive_policy.py
python src/scripts/select_best_adaptive_policy.py --help >/dev/null

echo "OK: select best adaptive policy compile"
