#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_RUNTIME_STRATEGY_RESOLVER_DATABASE_URL_PATCH_V1 ==="

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "EQUITY_RUNTIME_STRATEGY_RESOLVER_DATABASE_URL_PATCH_V1" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "psycopg2.connect(dsn)" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "runtime_active_universe" \
  src/finam_core/pipelines/paper_pipeline.py

echo "VERDICT=EQUITY_RUNTIME_STRATEGY_RESOLVER_DATABASE_URL_PATCH_OK"
echo "TEST_EQUITY_RUNTIME_STRATEGY_RESOLVER_DATABASE_URL_PATCH_V1_OK"
