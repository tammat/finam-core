#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_gold_shadow_stability_monitor_v1.py

python3 src/scripts/research/build_gold_shadow_stability_monitor_v1.py \
  | tee /tmp/gold_shadow_stability_monitor_v1.log

grep -q "GOLD SHADOW STABILITY MONITOR V1" /tmp/gold_shadow_stability_monitor_v1.log
grep -q "MONITOR_SUMMARY_ROW" /tmp/gold_shadow_stability_monitor_v1.log
grep -q "runtime_allow=0" /tmp/gold_shadow_stability_monitor_v1.log
grep -q "execution_enabled=0" /tmp/gold_shadow_stability_monitor_v1.log
grep -q "GOLD_SHADOW_STABILITY_MONITOR_V1_OK" /tmp/gold_shadow_stability_monitor_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    strategy,
    stability_ratio,
    negative_ratio,
    days_effective,
    days_stable,
    verdict,
    runtime_allowed,
    execution_enabled
FROM gold_shadow_stability_monitor
ORDER BY id DESC
LIMIT 1;
" | tee /tmp/gold_shadow_stability_monitor_db_v1.log

grep -q "GDU6@RTSX" /tmp/gold_shadow_stability_monitor_db_v1.log
grep -q "gold_short_only_shadow_v1" /tmp/gold_shadow_stability_monitor_db_v1.log
grep -q " f " /tmp/gold_shadow_stability_monitor_db_v1.log

echo TEST_GOLD_SHADOW_STABILITY_MONITOR_V1_OK
