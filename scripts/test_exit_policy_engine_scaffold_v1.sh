#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_EXIT_POLICY_ENGINE_SCAFFOLD_V1 ==="

python3 -m py_compile \
  src/finam_core/research/exit_policy/policy_base.py \
  src/finam_core/research/exit_policy/policy_registry.py \
  src/finam_core/research/exit_policy/replay_engine.py \
  src/finam_core/research/exit_policy/evaluator.py \
  src/finam_core/research/exit_policy/scorecard.py \
  src/finam_core/research/exit_policy/policies/time_stop_5m.py \
  src/scripts/research/build_exit_policy_engine_scaffold_v1.py

src/scripts/research/build_exit_policy_engine_scaffold_v1.py \
  | tee /tmp/exit_policy_engine_scaffold_v1.out

grep -q "POLICY name=TIME_STOP_5M" /tmp/exit_policy_engine_scaffold_v1.out
grep -q "EXIT_POLICY_ROW policy=TIME_STOP_5M" /tmp/exit_policy_engine_scaffold_v1.out
grep -q "VERDICT=EXIT_POLICY_ENGINE_SCAFFOLD_READY" /tmp/exit_policy_engine_scaffold_v1.out

echo "TEST_EXIT_POLICY_ENGINE_SCAFFOLD_V1_OK"
