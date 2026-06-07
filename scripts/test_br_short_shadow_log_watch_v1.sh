#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_short_shadow_log_watch_v1.py

python3 src/scripts/analytics/build_br_short_shadow_log_watch_v1.py --since "6 hours ago" | \
  tee /tmp/br_short_shadow_log_watch_v1.log

grep -q "BR SHORT SHADOW LOG WATCH V1" /tmp/br_short_shadow_log_watch_v1.log
grep -q "BR_SELL_CANDIDATES=" /tmp/br_short_shadow_log_watch_v1.log
grep -q "BR_SHORT_SHADOW_POLICY_ROWS=" /tmp/br_short_shadow_log_watch_v1.log
grep -q "VERDICT=" /tmp/br_short_shadow_log_watch_v1.log
grep -q "BR_SHORT_SHADOW_LOG_WATCH_V1_OK" /tmp/br_short_shadow_log_watch_v1.log

echo TEST_BR_SHORT_SHADOW_LOG_WATCH_V1_OK
