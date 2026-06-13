#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

python3 src/scripts/analytics/build_ng_quality_gate_effectiveness_v1.py | tee /tmp/ng_quality_gate_effectiveness_v1.log

grep -q "NG QUALITY GATE EFFECTIVENESS V1" /tmp/ng_quality_gate_effectiveness_v1.log
grep -q "GATE_EFFECTIVENESS" /tmp/ng_quality_gate_effectiveness_v1.log
grep -q "DELTA_PNL" /tmp/ng_quality_gate_effectiveness_v1.log
grep -q "NG_QUALITY_GATE_EFFECTIVENESS_V1_OK" /tmp/ng_quality_gate_effectiveness_v1.log

echo "TEST_NG_QUALITY_GATE_EFFECTIVENESS_V1_OK"
