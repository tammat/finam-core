#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NG M1 RUNTIME SYMBOLS NO STALE FALLBACK V1 ==="
echo "mode=diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py
grep -q "_runtime_active_symbols" src/finam_core/pipelines/paper_pipeline.py

bash scripts/test_ngq6_runtime_universe_seed_v1.sh
sudo systemctl restart finam-paper-pipeline.service

sleep 90

journalctl -u finam-paper-pipeline.service --since "3 minutes ago" --no-pager | \
grep -E "PIPE_NGQ6_M1_BAR_HANDLER_TRACE_V1|PIPE_SMART_ENTRY BUY symbol=NGQ6@RTSX|PIPE_TRADE_EXEC symbol=NGQ6@RTSX|PIPE_FILLED paper NGQ6@RTSX" | tail -120 || true

echo "NG_M1_RUNTIME_SYMBOLS_NO_STALE_FALLBACK_V1_OK"
