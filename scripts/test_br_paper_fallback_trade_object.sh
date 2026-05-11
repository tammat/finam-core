#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "class _PaperTrade" src/finam_core/pipelines/paper_pipeline.py
grep -q "trade.trade_source = \"paper\"" src/finam_core/pipelines/paper_pipeline.py
grep -q "self.pg_logger.log_trade(trade)" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_BR_PAPER_EXEC_ERROR" src/finam_core/pipelines/paper_pipeline.py
! grep -q "execution_type=\"paper_replay_fallback\"" src/finam_core/pipelines/paper_pipeline.py

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

echo "BR_PAPER_FALLBACK_TRADE_OBJECT_TEST_OK"
