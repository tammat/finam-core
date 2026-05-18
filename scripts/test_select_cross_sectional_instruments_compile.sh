#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/select_cross_sectional_instruments.py \
  src/finam_core/research/cross_sectional_selector.py

python src/scripts/select_cross_sectional_instruments.py --help >/dev/null

echo "OK: select_cross_sectional_instruments compile"
