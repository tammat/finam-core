#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/quarantine_orphan_trade_fills.py

grep -q "orphan_sell_without_position" src/scripts/quarantine_orphan_trade_fills.py
grep -q "is_invalid" src/scripts/quarantine_orphan_trade_fills.py
grep -q "TRADE_HYGIENE_ORPHAN_FILLS_SUMMARY" src/scripts/quarantine_orphan_trade_fills.py

echo "TEST_QUARANTINE_ORPHAN_TRADE_FILLS_OK"
