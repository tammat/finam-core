#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NGQ6 M1 BAR HANDLER TRACE V1 ==="
echo "mode=diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NGQ6_M1_BAR_HANDLER_TRACE_V1" src/finam_core/pipelines/paper_pipeline.py

bash scripts/test_ngq6_runtime_universe_seed_v1.sh
sudo systemctl restart finam-paper-pipeline.service

sleep 90

journalctl -u finam-paper-pipeline.service --since "3 minutes ago" --no-pager | \
grep -E "PIPE_NGQ6_M1_BAR_HANDLER_TRACE_V1|PIPE_NG_M1_STRATEGY_INIT symbol=NGQ6@RTSX|PIPE_NG_SIGNAL|NGQ6@RTSX|FILL|TRADE" | tail -160 || true

echo "NGQ6_M1_BAR_HANDLER_TRACE_V1_OK"
