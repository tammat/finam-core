#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/runtime/build_runtime_regime_cluster_gate_v1.py

grep -q "LOW_IMPULSE" \
  src/scripts/runtime/build_runtime_regime_cluster_gate_v1.py

grep -q "ALLOW_RESEARCH_GATE" \
  src/scripts/runtime/build_runtime_regime_cluster_gate_v1.py

grep -q "confirmed_research_cluster_but_runtime_disabled_by_maturity_phase" \
  src/scripts/runtime/build_runtime_regime_cluster_gate_v1.py

grep -q "RUNTIME_REGIME_CLUSTER_GATE_V1_OK" \
  src/scripts/runtime/build_runtime_regime_cluster_gate_v1.py

echo "RUNTIME_REGIME_CLUSTER_GATE_V1_TEST_OK"
