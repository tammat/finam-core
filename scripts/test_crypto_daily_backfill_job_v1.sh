#!/usr/bin/env bash
set -euo pipefail

bash -n scripts/ops/crypto_daily_backfill_job_v1.sh

grep -q "binance_crypto_backfill_v1.py" scripts/ops/crypto_daily_backfill_job_v1.sh
grep -q "build_crypto_research_dashboard_v1.py" scripts/ops/crypto_daily_backfill_job_v1.sh
grep -q "CRYPTO_DAILY_BACKFILL_JOB_V1_OK" scripts/ops/crypto_daily_backfill_job_v1.sh

echo CRYPTO_DAILY_BACKFILL_JOB_V1_OK
