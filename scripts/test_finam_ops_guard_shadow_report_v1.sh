#!/usr/bin/env bash
set -euo pipefail

bash -n scripts/ops/finam_ops.sh

grep -q "12) guard-shadow" scripts/ops/finam_ops.sh
grep -q "GUARD SHADOW REPORT" scripts/ops/finam_ops.sh
grep -q "build_guard_shadow_effectiveness_report_v1.py" scripts/ops/finam_ops.sh
grep -q "guard-shadow)" scripts/ops/finam_ops.sh

python3 -m py_compile src/scripts/analytics/build_guard_shadow_effectiveness_report_v1.py

echo FINAM_OPS_GUARD_SHADOW_REPORT_V1_OK
