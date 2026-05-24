#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

./scripts/run_selection_layer_v1.sh

PYTHONPATH=src python src/scripts/runtime/apply_active_contract_lifecycle_filter.py

echo "SELECTION_LAYER_WITH_ACTIVE_CONTRACT_FILTER_OK"
