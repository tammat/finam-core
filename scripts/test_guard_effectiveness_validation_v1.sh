#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_guard_effectiveness_validation_v1.py

python3 src/scripts/analytics/build_guard_effectiveness_validation_v1.py | tee /tmp/guard_effectiveness_validation_v1.log

grep -q "GUARD EFFECTIVENESS VALIDATION V1" /tmp/guard_effectiveness_validation_v1.log
grep -q "ALL_TRADES" /tmp/guard_effectiveness_validation_v1.log
grep -q "WITHOUT_BLOCK_READY" /tmp/guard_effectiveness_validation_v1.log
grep -q "DELTA" /tmp/guard_effectiveness_validation_v1.log
grep -Eq "VERDICT=GUARD_EFFECTIVE|VERDICT=GUARD_NOT_EFFECTIVE" /tmp/guard_effectiveness_validation_v1.log

echo GUARD_EFFECTIVENESS_VALIDATION_V1_OK
