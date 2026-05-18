#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/moex_find_security.py
python src/scripts/moex_find_security.py --help >/dev/null

echo "OK: moex_find_security compile"
