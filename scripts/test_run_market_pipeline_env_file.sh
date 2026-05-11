#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "FINAM_ENV_FILE" src/scripts/run_market_pipeline.py
grep -q "deploy/env/.env" src/scripts/run_market_pipeline.py
! grep -q "load_dotenv()" src/scripts/run_market_pipeline.py

python -m py_compile src/scripts/run_market_pipeline.py

echo "RUN_MARKET_PIPELINE_ENV_FILE_TEST_OK"
