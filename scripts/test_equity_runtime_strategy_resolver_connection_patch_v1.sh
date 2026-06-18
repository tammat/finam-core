#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY RUNTIME STRATEGY RESOLVER CONNECTION PATCH V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "EQUITY_RUNTIME_STRATEGY_RESOLVER_CONNECTION_PATCH_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "DATABASE_URL" src/finam_core/pipelines/paper_pipeline.py
grep -q "psycopg2.connect" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_RUNTIME_EQUITY_STRATEGY_RESOLVER_DB_CONNECT_ERROR" src/finam_core/pipelines/paper_pipeline.py
grep -q "select strategy" src/finam_core/pipelines/paper_pipeline.py
grep -q "from runtime_active_universe" src/finam_core/pipelines/paper_pipeline.py
grep -q "is_enabled = true" src/finam_core/pipelines/paper_pipeline.py

echo
echo "=== PATCHED CONNECTION FALLBACK LINES ==="
grep -n "EQUITY_RUNTIME_STRATEGY_RESOLVER_CONNECTION_PATCH_V1\\|DATABASE_URL\\|psycopg2.connect\\|PIPE_RUNTIME_EQUITY_STRATEGY_RESOLVER_DB_CONNECT_ERROR" \
  src/finam_core/pipelines/paper_pipeline.py

echo TEST_EQUITY_RUNTIME_STRATEGY_RESOLVER_CONNECTION_PATCH_V1_OK
