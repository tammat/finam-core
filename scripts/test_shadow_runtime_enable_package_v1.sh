#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_enable_package_v1.py

python3 src/scripts/runtime/build_shadow_runtime_enable_package_v1.py \
  | tee /tmp/shadow_runtime_enable_package_v1.log

grep -q "SHADOW RUNTIME ENABLE PACKAGE V1" /tmp/shadow_runtime_enable_package_v1.log
grep -q "GDU6@RTSX" /tmp/shadow_runtime_enable_package_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_enable_package_v1.log
grep -q "SHADOW_RUNTIME_ENABLED" /tmp/shadow_runtime_enable_package_v1.log
grep -q "shadow_runtime_allowed=1" /tmp/shadow_runtime_enable_package_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_enable_package_v1.log
grep -q "SUMMARY_ROW enabled=2 not_enabled=3" /tmp/shadow_runtime_enable_package_v1.log
grep -q "SHADOW_RUNTIME_ENABLE_PACKAGE_V1_OK" /tmp/shadow_runtime_enable_package_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    source,
    admission_decision,
    enable_status,
    shadow_runtime_allowed,
    execution_enabled
FROM shadow_runtime_enable_package
ORDER BY id DESC
LIMIT 5;
"

echo TEST_SHADOW_RUNTIME_ENABLE_PACKAGE_V1_OK
