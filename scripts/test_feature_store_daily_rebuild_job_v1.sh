#!/usr/bin/env bash
set -euo pipefail

bash -n scripts/ops/feature_store_daily_rebuild_job_v1.sh

grep -q "rebuild_feature_store_v1.py" scripts/ops/feature_store_daily_rebuild_job_v1.sh
grep -q "build_crypto_feature_dashboard_v1.py" scripts/ops/feature_store_daily_rebuild_job_v1.sh
grep -q "FEATURE_STORE_DAILY_REBUILD_JOB_V1_OK" scripts/ops/feature_store_daily_rebuild_job_v1.sh

./scripts/ops/feature_store_daily_rebuild_job_v1.sh | \
  tee /tmp/feature_store_daily_rebuild_job_v1.log

grep -q "FEATURE_STORE_DAILY_REBUILD JOB V1" /tmp/feature_store_daily_rebuild_job_v1.log || \
grep -q "FEATURE STORE DAILY REBUILD JOB V1" /tmp/feature_store_daily_rebuild_job_v1.log

grep -q "VERDICT=OK" /tmp/feature_store_daily_rebuild_job_v1.log
grep -q "FEATURE_STORE_DAILY_REBUILD_JOB_V1_OK" /tmp/feature_store_daily_rebuild_job_v1.log

echo TEST_FEATURE_STORE_DAILY_REBUILD_JOB_V1_OK
