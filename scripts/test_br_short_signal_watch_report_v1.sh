#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_short_signal_watch_report_v1.py

python3 src/scripts/analytics/build_br_short_signal_watch_report_v1.py --since "6 hours ago" | \
  tee /tmp/br_short_signal_watch_report_v1.log

grep -q "BR SHORT SIGNAL WATCH REPORT V1" /tmp/br_short_signal_watch_report_v1.log
grep -q "BR_BUY_CANDIDATES=" /tmp/br_short_signal_watch_report_v1.log
grep -q "BR_SELL_ENTRY_CANDIDATES=" /tmp/br_short_signal_watch_report_v1.log
grep -q "BR_EXIT_ENGINE_SELL=" /tmp/br_short_signal_watch_report_v1.log
grep -q "BR_SHORT_POLICY_ROWS=" /tmp/br_short_signal_watch_report_v1.log
grep -q "BR_SHORT_SIGNAL_WATCH_REPORT_V1_OK" /tmp/br_short_signal_watch_report_v1.log

echo TEST_BR_SHORT_SIGNAL_WATCH_REPORT_V1_OK
