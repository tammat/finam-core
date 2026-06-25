#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_SCORECARD_ENGINE_V1 ==="

src/scripts/research/build_shadow_runtime_scorecard_engine_v1.py --save \
| tee /tmp/shadow_runtime_scorecard_engine_v1.out

grep -q "SHADOW_RUNTIME_SCORECARD_ENGINE_V1" /tmp/shadow_runtime_scorecard_engine_v1.out
grep -q "scorecards=1" /tmp/shadow_runtime_scorecard_engine_v1.out
grep -q "total_events=1" /tmp/shadow_runtime_scorecard_engine_v1.out
grep -q "starting_events=1" /tmp/shadow_runtime_scorecard_engine_v1.out
grep -q "scorecard=MSC-000001" /tmp/shadow_runtime_scorecard_engine_v1.out
grep -q "VERDICT=SHADOW_RUNTIME_SCORECARD_ENGINE_V1_READY" /tmp/shadow_runtime_scorecard_engine_v1.out

echo "TEST_SHADOW_RUNTIME_SCORECARD_ENGINE_V1_OK"
