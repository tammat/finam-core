#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_usdrub_shadow_signal_research_v1.py

python3 src/scripts/research/build_usdrub_shadow_signal_research_v1.py \
  | tee /tmp/usdrub_shadow_signal_research_v1.log

grep -q "USDRUB SHADOW SIGNAL RESEARCH V1" /tmp/usdrub_shadow_signal_research_v1.log
grep -q "USDRUB_SIGNAL_SUMMARY" /tmp/usdrub_shadow_signal_research_v1.log
grep -q "runtime_allow=0" /tmp/usdrub_shadow_signal_research_v1.log
grep -q "execution_enabled=0" /tmp/usdrub_shadow_signal_research_v1.log
grep -q "USDRUB_SHADOW_SIGNAL_RESEARCH_V1_OK" /tmp/usdrub_shadow_signal_research_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    strategy,
    COUNT(*) AS signals,
    COUNT(*) FILTER (WHERE side='BUY') AS buy,
    COUNT(*) FILTER (WHERE side='SELL') AS sell,
    MIN(signal_ts) AS first_ts,
    MAX(signal_ts) AS last_ts
FROM usdrub_shadow_signals
WHERE symbol='USDRUBF@RTSX'
GROUP BY symbol, strategy;
" | tee /tmp/usdrub_shadow_signal_research_db_v1.log

grep -q "USDRUBF@RTSX" /tmp/usdrub_shadow_signal_research_db_v1.log
grep -q "usdrub_shadow_signal_research_v1" /tmp/usdrub_shadow_signal_research_db_v1.log

echo TEST_USDRUB_SHADOW_SIGNAL_RESEARCH_V1_OK
